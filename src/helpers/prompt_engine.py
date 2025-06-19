"""
Jinja2-based prompt engine for Maho.
Replaces the old file-based prompt system with a more powerful and structured approach.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jsonschema import validate, ValidationError

from .files import get_abs_path


@dataclass
class PromptMetadata:
    """Metadata for a prompt template."""
    version: str
    category: str
    description: Optional[str] = None
    required_vars: Optional[List[str]] = None
    optional_vars: Optional[List[str]] = None
    schema: Optional[Dict[str, Any]] = None


class PromptEngine:
    """Jinja2-based prompt engine with YAML frontmatter support."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = get_abs_path(prompts_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.prompts_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters
        self.env.filters['upper_first'] = self._upper_first
        self.env.filters['snake_to_title'] = self._snake_to_title
        
        # Cache for parsed templates
        self._template_cache: Dict[str, tuple[Template, PromptMetadata]] = {}
    
    def _upper_first(self, text: str) -> str:
        """Capitalize first letter."""
        return text[0].upper() + text[1:] if text else text
    
    def _snake_to_title(self, text: str) -> str:
        """Convert snake_case to Title Case."""
        return text.replace('_', ' ').title()
    
    def _parse_template_file(self, template_path: str) -> tuple[str, PromptMetadata]:
        """Parse a template file with YAML frontmatter."""
        full_path = Path(self.prompts_dir) / template_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for YAML frontmatter
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                # Has frontmatter
                frontmatter_yaml = parts[1]
                template_content = parts[2]
                
                try:
                    metadata_dict = yaml.safe_load(frontmatter_yaml)
                    metadata = PromptMetadata(**metadata_dict)
                except Exception as e:
                    raise ValueError(f"Invalid frontmatter in {template_path}: {e}")
            else:
                # Malformed frontmatter
                template_content = content
                metadata = PromptMetadata(version="1.0", category="unknown")
        else:
            # No frontmatter
            template_content = content
            metadata = PromptMetadata(version="1.0", category="unknown")
        
        return template_content, metadata
    
    def get_template(self, template_path: str) -> tuple[Template, PromptMetadata]:
        """Get a compiled template with metadata."""
        if template_path in self._template_cache:
            return self._template_cache[template_path]
        
        template_content, metadata = self._parse_template_file(template_path)
        template = self.env.from_string(template_content)
        
        self._template_cache[template_path] = (template, metadata)
        return template, metadata
    
    def render(self, template_path: str, **kwargs) -> str:
        """Render a template with the given variables."""
        template, metadata = self.get_template(template_path)
        
        # Validate required variables
        if metadata.required_vars:
            missing_vars = [var for var in metadata.required_vars if var not in kwargs]
            if missing_vars:
                raise ValueError(f"Missing required variables for {template_path}: {missing_vars}")
        
        # Validate against schema if provided
        if metadata.schema:
            try:
                validate(kwargs, metadata.schema)
            except ValidationError as e:
                raise ValueError(f"Template variables validation failed for {template_path}: {e}")
        
        return template.render(**kwargs)
    
    def render_string(self, template_string: str, **kwargs) -> str:
        """Render a template string directly."""
        template = self.env.from_string(template_string)
        return template.render(**kwargs)
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """List available templates, optionally filtered by category."""
        templates = []
        
        for root, dirs, files in os.walk(self.prompts_dir):
            for file in files:
                if file.endswith('.j2'):
                    rel_path = os.path.relpath(os.path.join(root, file), self.prompts_dir)
                    
                    if category:
                        try:
                            _, metadata = self.get_template(rel_path)
                            if metadata.category == category:
                                templates.append(rel_path)
                        except Exception:
                            continue
                    else:
                        templates.append(rel_path)
        
        return sorted(templates)
    
    def get_metadata(self, template_path: str) -> PromptMetadata:
        """Get metadata for a template without rendering."""
        _, metadata = self.get_template(template_path)
        return metadata


# Global prompt engine instance
_prompt_engine: Optional[PromptEngine] = None


def get_prompt_engine() -> PromptEngine:
    """Get the global prompt engine instance."""
    global _prompt_engine
    if _prompt_engine is None:
        _prompt_engine = PromptEngine()
    return _prompt_engine


def render_prompt(template_path: str, **kwargs) -> str:
    """Convenience function to render a prompt."""
    return get_prompt_engine().render(template_path, **kwargs)


def render_prompt_string(template_string: str, **kwargs) -> str:
    """Convenience function to render a prompt string."""
    return get_prompt_engine().render_string(template_string, **kwargs) 