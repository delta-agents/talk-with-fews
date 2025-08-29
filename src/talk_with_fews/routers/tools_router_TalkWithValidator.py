from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_fews.utils.docstring_generator import auto_docstring
from talk_with_fews.routers.setup_connections import get_runtime_ctx


# Import tool functions and their models
from talk_with_fews.tools.validator.validate_xml import validate_xml
from talk_with_fews.tools.validator.generate_xml_template import generate_xml_template
from talk_with_fews.tools.validator.get_available_elements import get_available_elements
from talk_with_fews.models.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
)
from talk_with_fews.models.generate_xml_template import (
    XMLTemplateInput,
    XMLTemplateOutput,
)
from talk_with_fews.models.get_available_elements import (
    GetAvailableElementsInput,
    GetAvailableElementsOutput,
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


# generate_xml_template tool registration
@mcp.tool()
@router.post("/tools.validator/generate_xml_template")
@auto_docstring(
    "Generate XML templates from XSD schemas using xmlschema package. "
    "This tool analyzes XSD schema files and generates valid XML templates with proper structure. "
    "Features include: "
    "- Automatic schema analysis and element discovery "
    "- Generation of complete XML templates with example values "
    "- Support for complex nested element structures "
    "- Proper namespace handling for FEWS schemas "
    "- Attribute inclusion with example values "
    "- Optional element handling based on schema definitions "
    "- Required target_element parameter to prevent long-running operations "
    "- Intelligent suggestions for similar elements when target not found "
    "- 5-second timeout protection to prevent hanging on complex schemas "
)
async def generate_xml_template_mcp(input: XMLTemplateInput) -> XMLTemplateOutput:
    ctx = get_runtime_ctx()
    return await generate_xml_template(ctx, input)


# get_available_elements tool registration
@mcp.tool()
@router.post("/tools.validator/get_available_elements")
@auto_docstring(
    "Get available elements from a FEWS schema with pagination and target element filtering. "
    "This tool analyzes a FEWS XSD schema and returns available element names "
    "that can be used as target_element in template generation. "
    "Features include: "
    "- Pagination support (default: 20 elements per page, max: 100) "
    "- Target element filtering to get elements within specific sub-elements "
    "- Complete element discovery from FEWS schemas "
    "- Support for complex nested element structures "
    "- Root element specification for focused element discovery "
    "- Total count and pagination information "
    "- Intelligent suggestions for invalid target elements "
    "- Useful for exploring large schema structures efficiently "
)
async def get_available_elements_mcp(
    input: GetAvailableElementsInput,
) -> GetAvailableElementsOutput:
    ctx = get_runtime_ctx()
    return await get_available_elements(ctx, input)
