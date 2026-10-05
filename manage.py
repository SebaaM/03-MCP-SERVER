#!/usr/bin/env python
"""Utilidad de gestión del proyecto Django del laboratorio (etapa 03)."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Ejecutaste `uv sync` en esta carpeta?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
