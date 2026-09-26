"""Request-local transport credentials, kept out of MCP tool arguments."""

from contextvars import ContextVar


_api_key = ContextVar("mcp_api_key", default=None)


def current_api_key():
    return _api_key.get()


def set_api_key(value):
    return _api_key.set(value)


def reset_api_key(token):
    _api_key.reset(token)

