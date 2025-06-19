import mimetypes
import os
import asyncio
import aiohttp
import json
from urllib.parse import urlparse
from typing import Sequence, List, Optional, Tuple
from datetime import datetime

from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_community.document_loaders.pdf import PyMuPDFLoader
from langchain_community.document_transformers import MarkdownifyTransformer
from langchain_community.document_loaders.parsers.images import TesseractBlobParser

try:
    from langchain_unstructured import UnstructuredLoader
except ImportError:
    UnstructuredLoader = None

from langchain_core.documents import Document
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.helpers.print_style import PrintStyle
from src.helpers import files
from src.core.agent import Agent
from src.helpers.vector_db import VectorDB


class DocumentQueryHelper:
    """Simplified document query helper that works with maho's current architecture."""

    def __init__(self, agent: Agent, progress_callback=None):
        self.agent = agent
        self.progress_callback = progress_callback
        self.vector_db = None
        self.documents = {}  # Simple in-memory cache

    def _log_progress(self, message: str):
        """Log progress if callback is provided."""
        if self.progress_callback:
            self.progress_callback(message)
        PrintStyle.standard(message)

    @staticmethod
    def normalize_uri(uri: str) -> str:
        """Normalize a document URI to ensure consistent lookup."""
        normalized = uri.strip()
        parsed = urlparse(normalized)
        scheme = parsed.scheme or "file"

        if scheme == "file":
            path = files.get_abs_path(
                normalized.removeprefix("file://").removeprefix("file:")
            )
            normalized = f"file://{path}"
        elif scheme in ["http", "https"]:
            normalized = normalized.replace("http://", "https://")

        return normalized

    async def document_qa(self, document_uri: str, questions: Sequence[str]) -> Tuple[bool, str]:
        """Answer questions about a document."""
        try:
            self._log_progress(f"Loading document: {document_uri}")
            content = await self.document_get_content(document_uri)
            
            if not content:
                return False, f"Could not load document: {document_uri}"

            # For now, use simple Q&A without vector search
            questions_str = "\n".join([f" * {question}" for question in questions])
            
            system_prompt = self.agent.read_prompt("fw.document_query.system_prompt.md")
            user_message = f"# Document:\n{content}\n\n# Queries:\n{questions_str}"

            self._log_progress("Generating answers...")
            ai_response = await self.agent.call_chat_model(
                prompt=ChatPromptTemplate.from_messages([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message),
                ])
            )

            return True, str(ai_response)
        except Exception as e:
            error_msg = f"Error in document Q&A: {str(e)}"
            self._log_progress(error_msg)
            return False, error_msg

    async def document_get_content(self, document_uri: str) -> str:
        """Get document content, with caching."""
        document_uri = self.normalize_uri(document_uri)
        
        # Check cache first
        if document_uri in self.documents:
            self._log_progress("Using cached document content")
            return self.documents[document_uri]

        try:
            url = urlparse(document_uri)
            scheme = url.scheme or "file"
            mimetype, encoding = mimetypes.guess_type(document_uri)
            mimetype = mimetype or "application/octet-stream"

            # Handle remote files
            if scheme in ["http", "https"]:
                self._log_progress("Checking remote document...")
                async with aiohttp.ClientSession() as session:
                    async with session.head(document_uri, timeout=aiohttp.ClientTimeout(total=5.0)) as response:
                        if response.status >= 400:
                            raise ValueError(f"Cannot access document: HTTP {response.status}")
                        
                        content_type = response.headers.get("content-type", mimetype)
                        if "content-length" in response.headers:
                            content_length = float(response.headers["content-length"]) / 1024 / 1024  # MB
                            if content_length > 50.0:
                                raise ValueError(f"Document too large: {content_length:.1f}MB (max 50MB)")
                        
                        if content_type and '; charset=' in content_type:
                            mimetype = content_type.split('; charset=')[0]

            # Handle local files
            elif scheme == "file":
                document_uri = files.get_abs_path(url.path)
                if not os.path.exists(document_uri):
                    raise ValueError(f"File not found: {document_uri}")

            if encoding:
                raise ValueError(f"Compressed documents not supported: {encoding}")

            # Load document based on type
            self._log_progress(f"Loading document ({mimetype})...")
            
            if mimetype.startswith("image/"):
                content = self._handle_image_document(document_uri, scheme)
            elif mimetype == "text/html":
                content = self._handle_html_document(document_uri, scheme)
            elif mimetype.startswith("text/") or mimetype == "application/json":
                content = self._handle_text_document(document_uri, scheme)
            elif mimetype == "application/pdf":
                content = self._handle_pdf_document(document_uri, scheme)
            else:
                content = self._handle_unstructured_document(document_uri, scheme)

            # Cache the content
            self.documents[document_uri] = content
            self._log_progress(f"Document loaded: {len(content)} characters")
            return content

        except Exception as e:
            error_msg = f"Error loading document {document_uri}: {str(e)}"
            self._log_progress(error_msg)
            raise ValueError(error_msg) from e

    def _handle_image_document(self, document: str, scheme: str) -> str:
        """Handle image documents using OCR."""
        return self._handle_unstructured_document(document, scheme)

    def _handle_html_document(self, document: str, scheme: str) -> str:
        """Handle HTML documents."""
        if scheme in ["http", "https"]:
            loader = AsyncHtmlLoader(web_path=document)
        elif scheme == "file":
            loader = TextLoader(file_path=document)
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")

        parts = loader.load()
        try:
            return "\n".join([element.page_content for element in MarkdownifyTransformer().transform_documents(parts)])
        except Exception:
            # Fallback to raw text if markdownify fails
            return "\n".join([element.page_content for element in parts])

    def _handle_text_document(self, document: str, scheme: str) -> str:
        """Handle plain text documents."""
        if scheme in ["http", "https"]:
            loader = AsyncHtmlLoader(web_path=document)
        elif scheme == "file":
            loader = TextLoader(file_path=document)
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")

        elements = loader.load()
        return "\n".join([element.page_content for element in elements])

    def _handle_pdf_document(self, document: str, scheme: str) -> str:
        """Handle PDF documents."""
        if scheme not in ["file", "http", "https"]:
            raise ValueError(f"Unsupported scheme: {scheme}")

        try:
            # Try with OCR support
            loader = PyMuPDFLoader(
                document,
                extract_images=True,
                images_inner_format="text",
                images_parser=TesseractBlobParser(),
            )
        except Exception:
            # Fallback without OCR
            loader = PyMuPDFLoader(document)

        elements = loader.load()
        return "\n".join([element.page_content for element in elements])

    def _handle_unstructured_document(self, document: str, scheme: str) -> str:
        """Handle documents using unstructured loader."""
        if UnstructuredLoader is None:
            raise ValueError("Unstructured loader not available")

        if scheme in ["http", "https"]:
            loader = UnstructuredLoader(
                web_url=document,
                mode="single",
                strategy="fast",  # Use fast strategy to avoid issues
            )
        elif scheme == "file":
            loader = UnstructuredLoader(
                file_path=document,
                mode="single",
                strategy="fast",
            )
        else:
            raise ValueError(f"Unsupported scheme: {scheme}")

        elements = loader.load()
        return "\n".join([element.page_content for element in elements])
