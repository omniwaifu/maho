#!/usr/bin/env python3
"""
Model preloading script for Maho.
This replaces the old preload.py file.
"""

import os
import sys
import json
import time
import uuid
import traceback
from pathlib import Path
import anyio

# Add the project root to Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.helpers import runtime, whisper, settings
from src.helpers.print_style import PrintStyle
from src.providers.base import ModelProvider


async def preload():
    PrintStyle().print("Running preload...")
    runtime.initialize()

    try:
        set = settings.get_default_settings()

        # preload whisper model
        async def preload_whisper():
            try:
                return await whisper.preload(set["stt_model_size"])
            except Exception as e:
                PrintStyle().error(f"Error in preload_whisper: {e}")

        # preload embedding model
        async def preload_embedding():
            if set["embed_model_provider"] == ModelProvider.HUGGINGFACE.name:
                try:
                    from src import models

                    emb_mod = models.get_huggingface_embedding(set["embed_model_name"])
                    emb_txt = await emb_mod.aembed_query("test")
                    return emb_txt
                except Exception as e:
                    PrintStyle().error(f"Error in preload_embedding: {e}")

        # Process tasks concurrently using anyio task group
        async with anyio.create_task_group() as tg:
            tg.start_soon(preload_whisper)
            tg.start_soon(preload_embedding)
        PrintStyle().print("Preload completed")

    except Exception as e:
        PrintStyle().error(f"Error in preload: {e}")


def main():
    anyio.run(preload)


if __name__ == "__main__":
    main()
