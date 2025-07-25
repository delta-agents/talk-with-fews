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

        # Build docstring
        doc_parts = []
        if description:
            doc_parts.append(description.strip())

        # Add input documentation
        if input_model:
            doc_parts.append("\nParameters:\n")
            doc_parts.append(
                f"- input ({input_model.__name__}): Input parameters for the tool"
            )
            doc_parts.append(generate_pydantic_docstring(input_model, indent=4))

            # Add JSON example
            doc_parts.append("\nExample input:")
            doc_parts.append("```json")
            doc_parts.append(generate_json_example(input_model))
            doc_parts.append("```")

        # Add return documentation
        if resolved_return_model:
            doc_parts.append("\nReturns:\n")
            doc_parts.append(
                f"- {resolved_return_model.__name__}: Output data from the tool"
            )
            doc_parts.append(
                generate_pydantic_docstring(resolved_return_model, indent=4)
            )

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
            else:
                field_type = f"List[{items_info.get('type', 'unknown')}]"

        elif "anyOf" in field_info:  # Handle Optional
            sub_types = [
                t.get("type", "unknown")
                for t in field_info["anyOf"]
                if t.get("type") != "null"
            ]
            field_type = f"Optional[{', '.join(sub_types)}]"

        # Add the field to the lines
        lines.append(
            f"{indent_str}- {field_name} ({field_type}, {req_flag}): {description}"
        )

    return "\n".join(lines)


def generate_json_example(model_class: type[BaseModel]) -> str:
    """
    Generate a JSON example from a Pydantic model.

    Args:
        model_class: The Pydantic model class

    Returns:
        A JSON example string
    """
    try:
        # Get the schema
        schema = model_class.model_json_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Build example JSON
        example = {}
        for field_name, field_info in properties.items():
            # Check if field is required
            is_required = field_name in required

            # Handle Optional types (anyOf with null)
            if "anyOf" in field_info:
                # Find the non-null type
                non_null_types = [
                    t for t in field_info["anyOf"] if t.get("type") != "null"
                ]
                if non_null_types:
                    field_type = non_null_types[0].get("type", "string")
                else:
                    field_type = "string"
            else:
                field_type = field_info.get("type", "string")

            # Generate example values based on type
            if field_type == "string":
                if "parameter" in field_name.lower():
                    example[field_name] = "Kwel"
                elif "location" in field_name.lower():
                    example[field_name] = "GPG_1698"
                else:
                    example[field_name] = "example_value"
            elif field_type == "integer":
                example[field_name] = 10
            elif field_type == "number":
                example[field_name] = 10
            elif field_type == "boolean":
                example[field_name] = True
            elif field_type == "array":
                example[field_name] = ["item1", "item2"]
            elif field_type == "object":
                example[field_name] = {"key": "value"}
            else:
                example[field_name] = None

            # For optional fields, we might want to omit them or set to null
            if not is_required and field_name in ["parameter_id", "location_id"]:
                # For mutually exclusive fields, only include one
                if field_name == "location_id":
                    example[field_name] = None

        # Convert to JSON string
        import json

        return json.dumps({"input": example}, indent=2)

    except Exception as e:
        return f'{{"input": {{"error": "Could not generate example: {e}"}}}}'
