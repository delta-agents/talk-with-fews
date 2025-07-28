from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_fews.utils.docstring_generator import auto_docstring
from talk_with_fews.routers.setup_connections import get_runtime_ctx


# Import tool functions and their models
from talk_with_fews.tools.validator.validate_xml import validate_xml
from talk_with_fews.models.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
)

router = APIRouter()
mcp = FastMCP("TalkWithFewsValidator")


# validate_xml tool registration
@mcp.tool()
@router.post("/tools.validator/validate_xml")
@auto_docstring(
    "Enhanced XML validation against FEWS schemas with intelligent snippet handling. "
    "This tool provides sophisticated XML validation capabilities specifically designed for FEWS XML snippets. "
    "Features include: "
    "- Auto-discovery of appropriate parent elements for XML snippets "
    "- Intelligent wrapping of nested XML snippets with correct parent structure "
    "- Validation against locally cached FEWS XSD schemas "
    "- Detailed error reporting with XPath debug information "
    "- Support for both direct and indirect parent element relationships "
    "- Automatic namespace prefix handling for FEWS schemas "
)
async def validate_xml_mcp(input: XMLValidationInput) -> XMLValidationOutput:
    ctx = get_runtime_ctx()
    return await validate_xml(ctx, input)
