"""
Tool for validating XML content against XSD schemas.
"""

from pydantic_ai import RunContext

from ...models.base import Deps
from ...utils.logging_utils import log_tool_call
from .xml_validator import XMLValidationInput, XMLValidationResult, create_validator


@log_tool_call
async def validate_xml(
    ctx: RunContext[Deps], input: XMLValidationInput
) -> XMLValidationResult:
    """
    Validate XML content against an XSD schema.

    This tool supports both full XML validation and partial validation using XPath.
    It can also cache schemas locally for offline use.

    Args:
        ctx: Runtime context
        input: XMLValidationInput containing XML content and validation parameters

    Returns:
        XMLValidationResult with validation status and any errors

    Example:
        ```python
        result = await validate_xml(ctx, XMLValidationInput(
            xml_content='<import>...</import>',
            schema_url='https://fewsdocs.deltares.nl/schemas/version1.0/timeSeriesImportRun.xsd',
            xpath='//import/general',  # Optional: validate only a specific part
            cache_schema=True  # Optional: cache schema locally
        ))
        ```
    """
    validator = create_validator(cache_dir=input.cache_dir)

    return validator.validate(
        xml_content=input.xml_content,
        schema_url=input.schema_url,
        xpath=input.xpath,
        cache_schema=input.cache_schema,
    )
