"""Model Context Protocol server exposing Venn decisions as a tool."""

from venn.client import Client


def create_server(endpoint="http://127.0.0.1:8000"):
    """Return an MCP server whose ``decide`` tool forwards to the Venn server at ``endpoint``.

    Supports the MCP Python SDK 2.x (``MCPServer``) and 1.x (``FastMCP``).
    """
    try:
        from mcp.server.mcpserver import MCPServer
    except ModuleNotFoundError as error:  # MCP 1.x
        if error.name not in ("mcp.server.mcpserver",):
            raise
        from mcp.server.fastmcp import FastMCP as MCPServer

    server = MCPServer("Venn")
    client = Client(endpoint)

    @server.tool()
    def decide(state: dict | list | str, questions: dict, model: str = "venn-1",
               experimental_media: bool = False) -> dict:
        """Ask typed per-item or Venn space-level questions. Never an authorization boundary."""
        return client.decide(state, questions, model=model, experimental_media=experimental_media)

    return server
