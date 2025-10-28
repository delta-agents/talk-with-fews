"""
Docstring generation utilities for FastAPI and MCP tools.

This module provides decorators and functions to automatically generate
documentation for API endpoints and tools based on Pydantic models.
"""

from typing import Callable, TypeVar, get_type_hints
from pydantic import BaseModel

T = TypeVar("T")


def auto_docstring(description: str = "", model_class: type[BaseModel] = None):
    """
    Decorator that automatically generates a docstring for MCP tools.

    Args:
        description: Description of what the tool does
        model_class: Optional Pydantic model class for return type
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get type hints
        type_hints = get_type_hints(func)

        # Get return type from type hints if model_class isn't explicitly given
        return_type = type_hints.get("return")
        resolved_return_model = model_class or (
            return_type if hasattr(return_type, "model_json_schema") else None
        )

        # Get input model from the first parameter (typically named 'input')
        input_model = None
        for param_name, param_type in type_hints.items():
            if param_name != "return" and hasattr(param_type, "model_json_schema"):
                input_model = param_type
                break

        # Build docstring following Google-style format
        doc_parts = []

        # Main description
        if description:
            # Clean up description and format bullet points properly
            clean_description = description.strip()
            # Convert bullet points to proper markdown format
            clean_description = clean_description.replace("- ", "\n- ")
            doc_parts.append(clean_description)

        # Add input documentation
        if input_model:
            doc_parts.append("\nArgs:")
            doc_parts.append(
                f"    input ({input_model.__name__}): Input parameters as JSON object for the tool"
            )

            # Add detailed parameter documentation
            param_details = generate_pydantic_docstring(input_model, indent=8)
            if param_details:
                doc_parts.append(param_details)

        # Add return documentation
        if resolved_return_model:
            doc_parts.append("\nReturns:")
            doc_parts.append(
                f"    {resolved_return_model.__name__}: Output data from the tool"
            )

            # Add detailed return documentation
            return_details = generate_pydantic_docstring(
                resolved_return_model, indent=8
            )
            if return_details:
                doc_parts.append(return_details)

        # Combine with existing docstring if any
        existing_doc = func.__doc__ or ""
        func.__doc__ = "\n".join([existing_doc.strip(), *doc_parts]).strip()

        return func

    return decorator


def generate_pydantic_docstring(
    model_class: type[BaseModel], indent: int = 4, _visited=None, max_depth: int = 3
) -> str:
    """
    Generate a formatted docstring from a Pydantic model.

    Args:
        model_class: The Pydantic model class
        indent: Number of spaces for indentation
        _visited: Internal set to avoid recursion loops
        max_depth: Maximum depth for nested models

    Returns:
        A formatted docstring string
    """
    _visited = _visited or set()
    current_depth = len(_visited)

    if current_depth >= max_depth:
        return f"{' ' * indent}- {model_class.__name__}: [Nested structure - see model definition]"

    indent_str = " " * indent
    lines = []

    schema = model_class.model_json_schema()
    properties = schema.get("properties", {})

    for field_name, field_info in properties.items():
        # Determine type
        field_type = field_info.get("type", "unknown")
        description = field_info.get("description", "No description provided")
        required = field_name in schema.get("required", [])

        # Mark required - define req_flag early
        req_flag = "required" if required else "optional"

        # Check nested models
        # nested_model = None  # noqa: F841
        if "$ref" in field_info:
            ref_name = field_info["$ref"].split("/")[-1]
            field_type = ref_name
            # Try to find the nested model using the schema definitions
            definitions = schema.get("$defs", {})
            if ref_name in definitions:
                # We found a nested model definition
                nested_schema = definitions[ref_name]
                if nested_schema.get("type") == "object":
                    # This is a nested object, we can show its structure
                    nested_properties = nested_schema.get("properties", {})
                    if nested_properties:
                        lines.append(
                            f"{indent_str}- {field_name} ({field_type}, {req_flag}): {description}"
                        )
                        # Show nested properties
                        for nested_field, nested_info in nested_properties.items():
                            # Handle nested anyOf fields
                            if "anyOf" in nested_info:
                                sub_types = []
                                for t in nested_info["anyOf"]:
                                    if t.get("type") == "null":
                                        continue  # Skip null types
                                    elif "$ref" in t:
                                        ref_name = t["$ref"].split("/")[-1]
                                        sub_types.append(ref_name)
                                    else:
                                        sub_types.append(t.get("type", "unknown"))

                                if len(sub_types) == 1:
                                    nested_type = f"Optional[{sub_types[0]}]"
                                elif len(sub_types) > 1:
                                    nested_type = f"Optional[{' | '.join(sub_types)}]"
                                else:
                                    nested_type = "unknown"
                            else:
                                nested_type = nested_info.get("type", "unknown")

                            nested_desc = nested_info.get(
                                "description", "No description"
                            )
                            nested_req = nested_field in nested_schema.get(
                                "required", []
                            )
                            nested_req_flag = "required" if nested_req else "optional"
                            lines.append(
                                f"{indent_str}    - {nested_field} ({nested_type}, {nested_req_flag}): {nested_desc}"
                            )
                        continue

        elif "items" in field_info:  # Handle lists
            items_info = field_info["items"]
            if "$ref" in items_info:
                ref_name = items_info["$ref"].split("/")[-1]
                field_type = f"List[{ref_name}]"
                # Try to find the nested model using the schema definitions
                definitions = schema.get("$defs", {})
                if ref_name in definitions:
                    nested_schema = definitions[ref_name]
                    if nested_schema.get("type") == "object":
                        nested_properties = nested_schema.get("properties", {})
                        if nested_properties:
                            lines.append(
                                f"{indent_str}- {field_name} ({field_type}, {req_flag}): {description}"
                            )
                            # Show nested properties
                            for nested_field, nested_info in nested_properties.items():
                                # Handle nested anyOf fields
                                if "anyOf" in nested_info:
                                    sub_types = []
                                    for t in nested_info["anyOf"]:
                                        if t.get("type") == "null":
                                            continue  # Skip null types
                                        elif "$ref" in t:
                                            ref_name = t["$ref"].split("/")[-1]
                                            sub_types.append(ref_name)
                                        else:
                                            sub_types.append(t.get("type", "unknown"))

                                    if len(sub_types) == 1:
                                        nested_type = f"Optional[{sub_types[0]}]"
                                    elif len(sub_types) > 1:
                                        nested_type = (
                                            f"Optional[{' | '.join(sub_types)}]"
                                        )
                                    else:
                                        nested_type = "unknown"
                                else:
                                    nested_type = nested_info.get("type", "unknown")

                                nested_desc = nested_info.get(
                                    "description", "No description"
                                )
                                nested_req = nested_field in nested_schema.get(
                                    "required", []
                                )
                                nested_req_flag = (
                                    "required" if nested_req else "optional"
                                )
                                lines.append(
                                    f"{indent_str}    - {nested_field} ({nested_type}, {nested_req_flag}): {nested_desc}"
                                )
                            continue
            elif "anyOf" in items_info:  # Handle union types in lists
                # Extract all non-null types from anyOf
                union_types = []
                for union_item in items_info["anyOf"]:
                    if "$ref" in union_item:
                        ref_name = union_item["$ref"].split("/")[-1]
                        union_types.append(ref_name)
                    elif union_item.get("type") != "null":
                        union_types.append(union_item.get("type", "unknown"))
                field_type = (
                    f"List[{' | '.join(union_types)}]"
                    if union_types
                    else "List[unknown]"
                )
            else:
                field_type = f"List[{items_info.get('type', 'unknown')}]"

        elif "anyOf" in field_info:  # Handle Optional and Union types
            sub_types = []
            for t in field_info["anyOf"]:
                if t.get("type") == "null":
                    continue  # Skip null types
                elif "$ref" in t:
                    ref_name = t["$ref"].split("/")[-1]
                    sub_types.append(ref_name)
                else:
                    sub_types.append(t.get("type", "unknown"))

            if len(sub_types) == 1:
                field_type = f"Optional[{sub_types[0]}]"
            elif len(sub_types) > 1:
                field_type = f"Optional[{' | '.join(sub_types)}]"
            else:
                field_type = "unknown"

        # Add the field to the lines
        lines.append(
            f"{indent_str}- {field_name} ({field_type}, {req_flag}): {description}"
        )

    return "\n".join(lines)
