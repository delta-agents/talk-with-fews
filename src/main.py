from dotenv import load_dotenv
load_dotenv(dotenv_path="env/.env")

from fastapi import FastAPI
from talk_with_fews.routers.tools_router import router, mcp

# Mount MCP at /mcp
mcp_app = mcp.http_app(path='/', transport="streamable-http")

app = FastAPI(
    title="Talk with FEWS Tools API",
    version="0.1.0",
    description="API and MCP server exposing selected tools",
    lifespan=mcp_app.lifespan
)

# Include the tools router
app.include_router(router)

# Mount MCP at /mcp
app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 