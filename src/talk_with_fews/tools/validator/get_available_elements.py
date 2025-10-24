"""
Tool for getting available elements from FEWS schemas.

This module provides functionality to retrieve available elements
from FEWS XSD schemas with pagination support.
"""

from talk_with_fews.models.validator.get_available_elements import (
    GetAvailableElementsInput,
    GetAvailableElementsOutput,
)
from .generate_xml_template import XMLTemplateGenerator
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def get_available_elements(
    ctx, input: GetAvailableElementsInput
) -> GetAvailableElementsOutput:
    """
    Get available elements from a FEWS schema with pagination support.

    This tool analyzes a FEWS XSD schema and returns available element names
    that can be used as target_element in template generation.
    Supports pagination to handle large schemas efficiently.
    """
    # Get schema cache directory from context
    schemas_dir = ctx.deps.cache_fews_schemas_dir

    # Create generator instance
    generator = XMLTemplateGenerator(schemas_dir)

    # Convert enum to full schema path
    schema_url = f"data/fews_schemas/fewsdocs_deltares_nl/{input.schema_option.value}"

    # Validate pagination parameters
    limit = input.limit or 20
    offset = input.offset or 0

    # Enforce maximum limit
    if limit > 100:
        limit = 100

    # Ensure non-negative values
    if limit < 0:
        limit = 20
    if offset < 0:
        offset = 0

    # Get available elements (with optional target_element filtering)
    try:
        all_elements = await generator.get_available_elements(
            schema_url=schema_url,
            root_element=input.root_element,
            target_element=input.target_element,
        )
    except ValueError as e:
        # If target element not found, provide suggestions
        if "not found in schema" in str(e):
            # Get all available elements to provide suggestions
            try:
                all_elements = await generator.get_available_elements(
                    schema_url=schema_url,
                    root_element=input.root_element,
                )

                # Find similar elements using fuzzy matching
                similar_elements = generator._find_similar_elements(
                    input.target_element, set(all_elements)
                )

                # Build informative error message
                error_message = f"Target element '{input.target_element}' not found in schema '{input.schema_option.value}'."

                if similar_elements:
                    error_message += "\n\nSimilar elements found:\n"
                    for elem in similar_elements:
                        error_message += f"  - {elem}\n"
                else:
                    error_message += "\n\nAvailable elements (showing first 10):\n"
                    for elem in all_elements[:10]:
                        error_message += f"  - {elem}\n"
                    if len(all_elements) > 10:
                        error_message += (
                            f"  ... and {len(all_elements) - 10} more elements"
                        )

                error_message += (
                    "\n\nPlease try again with one of the suggested elements."
                )

                # Raise ModelRetry with suggestions
                from pydantic_ai import ModelRetry

                model_retry = ModelRetry(error_message)
                model_retry.__cause__ = None
                model_retry.__traceback__ = None
                raise model_retry
            except Exception:
                # If we can't get available elements, just raise the original error
                raise ValueError(str(e))
        else:
            # Re-raise other ValueError exceptions as-is
            raise ValueError(str(e))

    # Apply pagination
    total_count = len(all_elements)
    start_index = offset
    end_index = min(start_index + limit, total_count)

    # Get the requested slice
    available_elements = all_elements[start_index:end_index]

    # Calculate pagination info
    has_more = end_index < total_count
    next_offset = end_index if has_more else None

    # Determine root element from schema
    schema = await generator._load_schema(schema_url)
    root_element = input.root_element
    if not root_element and schema.root_elements:
        root_element = schema.root_elements[0].name
    elif not root_element:
        root_element = "unknown"

    return GetAvailableElementsOutput(
        schema_location=schema_url,
        root_element=root_element,
        target_element=input.target_element,
        available_elements=available_elements,
        total_count=total_count,
        limit=len(available_elements),
        offset=offset,
        has_more=has_more,
        next_offset=next_offset,
    )
