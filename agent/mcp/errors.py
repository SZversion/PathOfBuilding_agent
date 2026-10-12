"""Typed failures crossing the MCP tool boundary."""


class ToolCallError(RuntimeError):
    """A structured tool failure returned with MCP isError=true."""

    def __init__(self, error):
        self.error = error if isinstance(error, dict) else {}
        super().__init__(self.error.get("message", "MCP tool call failed"))
