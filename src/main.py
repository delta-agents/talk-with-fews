from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from talk_with_fews.routers.tools_router_TalkWithConfig import (
    router as router_talk_with_config,
)
from talk_with_fews.routers.tools_router_TalkWithConfig import (
    mcp as mcp_talk_with_config,
)
from talk_with_fews.routers.tools_router_TalkWithWebservice import (
    router as router_talk_with_webservice,
)
from talk_with_fews.routers.tools_router_TalkWithWebservice import (
    mcp as mcp_talk_with_webservice,
)

from typing import AsyncIterator
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv(dotenv_path="env/.env")

## Talk With Config

# Mount MCP at /mcp
mcp_app_config = mcp_talk_with_config.http_app(
    path="/", transport="streamable-http", stateless_http=True
)

mcp_app_webservice = mcp_talk_with_webservice.http_app(
    path="/", transport="streamable-http", stateless_http=True
)


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run both lifespans in startup
    async with (
        mcp_app_config.lifespan(mcp_app_config),
        mcp_app_webservice.lifespan(mcp_app_webservice),
    ):
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

# Include the tools router
app.include_router(router_talk_with_config)

# Mount MCP at /mcp
app.mount("/mcp/TalkWithConfig", mcp_app_config)

# Include the tools router
app.include_router(router_talk_with_webservice)

# Mount MCP at /mcp
app.mount("/mcp/TalkWithWebservice", mcp_app_webservice)
