from fastapi import FastAPI
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

from dotenv import load_dotenv

load_dotenv(dotenv_path="env/.env")

## Talk With Config

# Mount MCP at /mcp
mcp_app_config = mcp_talk_with_config.http_app(
    path="/", transport="streamable-http", stateless_http=True
)

app = FastAPI(
    title="Talk with FEWS Config Tools API",
    version="0.1.0",
    description="API and MCP server exposing selected tools",
    lifespan=mcp_app_config.lifespan,
)

# Include the tools router
app.include_router(router_talk_with_config)

# Mount MCP at /mcp
app.mount("/mcp/TalkWithConfig", mcp_app_config)


## Talk With Webservice

mcp_app_webservice = mcp_talk_with_webservice.http_app(
    path="/", transport="streamable-http", stateless_http=True
)

# Include the tools router
app.include_router(router_talk_with_webservice)

# Mount MCP at /mcp
app.mount("/mcp/TalkWithWebservice", mcp_app_webservice)
