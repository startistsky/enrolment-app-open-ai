import asyncio
import json
import os

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://localhost:9001/mcp",
)

MCP_REQUEST_TIMEOUT_SECONDS = 10


def _normalise_mcp_result(tool_result):
    """Convert an MCP result into normal Python data."""

    structured_content = getattr(
        tool_result,
        "structured_content",
        None
    )

    if structured_content is not None:
        return structured_content

    content = getattr(tool_result, "content", [])

    if (
        content
        and all(
            getattr(item, "type", None) == "text"
            for item in content
        )
    ):
        text_values = [
            item.text
            for item in content
        ]

        if len(text_values) == 1:
            try:
                return json.loads(text_values[0])
            except (TypeError, ValueError):
                return text_values[0]

        return text_values

    return [
        item.model_dump(
            by_alias=True,
            mode="json"
        )
        if hasattr(item, "model_dump")
        else str(item)
        for item in content
    ]


def _exception_contains(exception, exception_types):
    """Check nested MCP connection errors."""

    if isinstance(exception, exception_types):
        return True

    nested_exceptions = getattr(
        exception,
        "exceptions",
        ()
    )

    return any(
        _exception_contains(
            nested,
            exception_types
        )
        for nested in nested_exceptions
    )


def call_mcp_tool(tool_name, arguments=None):
    """Call one tool on the shared MCP Server."""

    async def invoke_tool():

        async with httpx.AsyncClient(
            timeout=MCP_REQUEST_TIMEOUT_SECONDS
        ) as http_client:

            async with streamable_http_client(
                MCP_SERVER_URL,
                http_client=http_client,
            ) as streams:

                async with ClientSession(
                    streams[0],
                    streams[1],
                    read_timeout_seconds=MCP_REQUEST_TIMEOUT_SECONDS,
                ) as session:

                    await session.initialize()

                    return await session.call_tool(
                        tool_name,
                        arguments or {}
                    )

    try:
        tool_result = asyncio.run(
            invoke_tool()
        )

    except Exception as exc:

        if _exception_contains(
            exc,
            (
                httpx.ConnectError,
                httpx.TimeoutException,
            ),
        ):
            return {
                "ok": False,
                "status": 503,
                "error": "MCP server unavailable",
                "detail": str(exc),
            }

        return {
            "ok": False,
            "status": 502,
            "error": "MCP protocol or tool invocation failed",
            "detail": str(exc),
        }

    if getattr(
        tool_result,
        "is_error",
        False
    ):
        return {
            "ok": False,
            "status": 502,
            "error": "MCP tool invocation failed",
            "detail": _normalise_mcp_result(
                tool_result
            ),
        }

    return {
        "ok": True,
        "result": _normalise_mcp_result(
            tool_result
        ),
    }