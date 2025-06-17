#!/usr/bin/env python3
"""
Environment preparation script for Agent Zero.
This replaces the old prepare.py file.
"""

import os
import sys
import string
import random

# Add the project root to Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.helpers import dotenv, runtime, settings
from src.helpers.print_style import PrintStyle


def main():
    PrintStyle.standard("Preparing environment...")

    try:
        runtime.initialize()

        # generate random root password if not set (for SSH)
        root_pass = dotenv.get_dotenv_value(dotenv.KEY_ROOT_PASSWORD)
        if not root_pass:
            root_pass = "".join(
                random.choices(string.ascii_letters + string.digits, k=32)
            )
            PrintStyle.standard("Changing root password...")
        settings.set_root_password(root_pass)

    except Exception as e:
        PrintStyle.error(f"Error in prepare: {e}")


if __name__ == "__main__":
    main()
