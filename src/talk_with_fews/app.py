"""FastAPI app that serves the Talk with FEWS tools over REST and MCP.

Start it with::

    uvicorn talk_with_fews.app:app --host 0.0.0.0 --port 8000

By default all MCP servers are mounted. Set ``TALK_WITH_FEWS_SERVERS`` to a
comma-separated subset (for example ``config``) to mount only those.
Servers that are not selected are never imported.
"""

import importlib
import os
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator, Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# server name -> (router module, MCP mount path)
SERVERS = {
    "config": (
        "talk_with_fews.routers.tools_router_TalkWithConfig",
        "/mcp/TalkWithConfig",
    ),
    "webservice": (
        "talk_with_fews.routers.tools_router_TalkWithWebservice",
        "/mcp/TalkWithWebservice",
    ),
    "validator": (
        "talk_with_fews.routers.tools_router_TalkWithValidator",
        "/mcp/TalkWithValidator",
    ),
}


def _servers_from_env() -> list[str]:
    value = os.getenv("TALK_WITH_FEWS_SERVERS", "")
    names = [name.strip() for name in value.split(",") if name.strip()]
    return names or list(SERVERS)


def create_app(servers: Iterable[str] | None = None) -> FastAPI:
    """Build the API with the selected MCP servers mounted.

    Args:
        servers: Names from ``SERVERS`` to mount. Defaults to the
            ``TALK_WITH_FEWS_SERVERS`` environment variable, or all servers
            when that is not set.

    Returns:
        A FastAPI app with a REST router and an MCP endpoint per server.
    """
    names = list(servers) if servers is not None else _servers_from_env()
    unknown = sorted(set(names) - set(SERVERS))
    if unknown:
        raise ValueError(f"Unknown server(s) {unknown}; choose from {sorted(SERVERS)}")

    mounts = []
    for name in names:
        module_name, mount_path = SERVERS[name]
        module = importlib.import_module(module_name)
        mcp_app = module.mcp.http_app(
            path="/", transport="streamable-http", stateless_http=True
        )
        mounts.append((module.router, mount_path, mcp_app))

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Each mounted MCP app needs its own lifespan to run.
        async with AsyncExitStack() as stack:
            for _, _, mcp_app in mounts:
                await stack.enter_async_context(mcp_app.lifespan(mcp_app))
            yield

    app = FastAPI(
        title="Talk with FEWS Tools API",
        version="0.1.0",
        description="API and MCP server exposing selected tools",
        lifespan=combined_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router, mount_path, mcp_app in mounts:
        app.include_router(router)
        app.mount(mount_path, mcp_app)

    return app


app = create_app()
