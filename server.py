"""Lanzador desde la raíz del laboratorio.

Mantiene importables tanto ``mcp_server`` como ``activities`` cuando Inspector
ejecuta el servidor como un archivo.
"""

from mcp_server.server import mcp


if __name__ == "__main__":
    mcp.run()
