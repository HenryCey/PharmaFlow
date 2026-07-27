#!/usr/bin/env python
"""PharmaFlow management entrypoint."""
import os
import sys


def main():
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and available on your PYTHONPATH? "
            "Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
