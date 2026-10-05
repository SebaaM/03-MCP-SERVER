"""Punto de entrada del servidor MCP para el proyecto Django."""

import os
import sys
from pathlib import Path

# Asegurar que Django esté configurado cuando el servidor corre fuera de manage.py
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    import django
except ImportError:
    django = None

if django is not None:
    django.setup()

from mcp.server import MCPServer

from mcp_server.prompts import register_prompts
from mcp_server.resources import register_resources
from mcp_server.tools import register_tools

mcp = MCPServer("Actividades UNTDF")
register_resources(mcp)
register_tools(mcp)
register_prompts(mcp)


if __name__ == "__main__":
    mcp.run()
