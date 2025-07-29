"""
Generate XML templates from XSD schemas using xmlschema package.

This module provides functionality to generate XML templates from XSD schemas
using the xmlschema package's code generation capabilities.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import xmlschema

from talk_with_fews.models.generate_xml_template import (
    XMLTemplateInput,
    XMLTemplateOutput,
)


class XMLTemplateGenerator:
    """Generate XML templates from XSD schemas using xmlschema"""

    def __init__(self, schemas_dir: str = "data/fews_schemas"):
        self.schemas_dir = Path(schemas_dir)
        self._schema_cache = {}

    async def generate_template(
        self,
        schema_url: str,
        root_element: Optional[str] = None,
        include_optional: bool = True,
        include_attributes: bool = True,
    ) -> str:
        """
        Generate an XML template from an XSD schema.

        Args:
            schema_url: Path to the XSD schema file
            root_element: Specific root element to generate template for (if None, uses first available)
            include_optional: Whether to include optional elements
            include_attributes: Whether to include attributes

        Returns:
            Generated XML template as string
        """
        # Load schema
        schema = await self._load_schema(schema_url)

        # Determine root element
        if not root_element:
            root_elements = schema.root_elements
            if not root_elements:
                raise ValueError("No root elements found in schema")
            root_element = root_elements[0].name

        # Generate template structure
        template_structure = self._generate_element_structure(
            schema, root_element, include_optional, include_attributes
        )

        # Create XML template
        xml_template = self._create_xml_template(template_structure, schema)

        return xml_template

    async def _load_schema(self, schema_path: str) -> xmlschema.XMLSchema:
        """Load schema from local cache with caching"""
        if schema_path in self._schema_cache:
            return self._schema_cache[schema_path]

        # Handle both relative and absolute paths
        if Path(schema_path).is_absolute() or schema_path.startswith("data/"):
            full_path = Path(schema_path)
        else:
            full_path = self.schemas_dir / schema_path

        if not full_path.exists():
            raise ValueError(f"Schema not found: {schema_path}")

        schema = xmlschema.XMLSchema(str(full_path), validation="lax")
        self._schema_cache[schema_path] = schema
        return schema

    def _generate_element_structure(
        self,
        schema: xmlschema.XMLSchema,
        element_name: str,
        include_optional: bool,
        include_attributes: bool,
    ) -> Dict[str, Any]:
        """Generate element structure from schema"""
        structure = {
            "name": element_name,
            "attributes": [],
            "children": [],
            "text_content": None,
        }

        # Find element in schema
        if element_name in schema.elements:
            element = schema.elements[element_name]

            # Handle attributes
            if include_attributes and hasattr(element, "attributes"):
                for attr_name, attr_obj in element.attributes.items():
                    attr_info = {
                        "name": attr_name,
                        "required": getattr(attr_obj, "use", "optional") == "required",
                        "default": getattr(attr_obj, "default", None),
                        "type": str(getattr(attr_obj, "type", "string")),
                    }
                    structure["attributes"].append(attr_info)

            # Handle content
            if hasattr(element, "type") and element.type:
                if element.type.is_simple():
                    # Simple type - can have text content
                    structure["text_content"] = self._get_example_value(element.type)
                elif element.type.is_complex():
                    # Complex type - has child elements
                    structure["children"] = self._get_child_elements(
                        element.type, include_optional
                    )
        else:
            # Try to find by local name (without namespace)
            local_name = (
                element_name.split("}")[-1] if "}" in element_name else element_name
            )
            for elem_name, elem_obj in schema.elements.items():
                elem_local_name = (
                    elem_name.split("}")[-1] if "}" in elem_name else elem_name
                )
                if elem_local_name == local_name:
                    # Found the element, now process it
                    if include_attributes and hasattr(elem_obj, "attributes"):
                        for attr_name, attr_obj in elem_obj.attributes.items():
                            attr_info = {
                                "name": attr_name,
                                "required": getattr(attr_obj, "use", "optional")
                                == "required",
                                "default": getattr(attr_obj, "default", None),
                                "type": str(getattr(attr_obj, "type", "string")),
                            }
                            structure["attributes"].append(attr_info)

                    if hasattr(elem_obj, "type") and elem_obj.type:
                        if elem_obj.type.is_simple():
                            structure["text_content"] = self._get_example_value(
                                elem_obj.type
                            )
                        elif elem_obj.type.is_complex():
                            structure["children"] = self._get_child_elements(
                                elem_obj.type, include_optional
                            )
                    break

        return structure

    def _get_child_elements(
        self, type_obj, include_optional: bool
    ) -> List[Dict[str, Any]]:
        """Get child elements from complex type"""
        children = []

        try:
            # Try different methods to get child elements
            if hasattr(type_obj, "iter_elements"):
                for child_elem in type_obj.iter_elements():
                    if hasattr(child_elem, "name") and child_elem.name:
                        # Check if element is optional
                        min_occurs = getattr(child_elem, "min_occurs", 1)
                        max_occurs = getattr(child_elem, "max_occurs", 1)

                        if not include_optional and min_occurs == 0:
                            continue

                        child_info = {
                            "name": child_elem.name,
                            "required": min_occurs > 0,
                            "multiple": max_occurs == "unbounded"
                            or (max_occurs is not None and max_occurs > 1),
                            "min_occurs": min_occurs,
                            "max_occurs": max_occurs,
                            "attributes": [],
                            "children": [],
                            "text_content": None,
                        }

                        # Recursively get child structure
                        if hasattr(child_elem, "type") and child_elem.type:
                            if child_elem.type.is_simple():
                                child_info["text_content"] = self._get_example_value(
                                    child_elem.type
                                )
                            elif child_elem.type.is_complex():
                                child_info["children"] = self._get_child_elements(
                                    child_elem.type, include_optional
                                )

                        children.append(child_info)

            # Try content model
            elif hasattr(type_obj, "content") and type_obj.content:
                if hasattr(type_obj.content, "iter_elements"):
                    for child_elem in type_obj.content.iter_elements():
                        if hasattr(child_elem, "name") and child_elem.name:
                            min_occurs = getattr(child_elem, "min_occurs", 1)
                            max_occurs = getattr(child_elem, "max_occurs", 1)

                            if not include_optional and min_occurs == 0:
                                continue

                            child_info = {
                                "name": child_elem.name,
                                "required": min_occurs > 0,
                                "multiple": max_occurs == "unbounded"
                                or (max_occurs is not None and max_occurs > 1),
                                "min_occurs": min_occurs,
                                "max_occurs": max_occurs,
                                "attributes": [],
                                "children": [],
                                "text_content": None,
                            }

                            if hasattr(child_elem, "type") and child_elem.type:
                                if child_elem.type.is_simple():
                                    child_info["text_content"] = (
                                        self._get_example_value(child_elem.type)
                                    )
                                elif child_elem.type.is_complex():
                                    child_info["children"] = self._get_child_elements(
                                        child_elem.type, include_optional
                                    )

                            children.append(child_info)

            # Try model group
            elif hasattr(type_obj, "model_group") and type_obj.model_group:
                if hasattr(type_obj.model_group, "iter_elements"):
                    for child_elem in type_obj.model_group.iter_elements():
                        if hasattr(child_elem, "name") and child_elem.name:
                            min_occurs = getattr(child_elem, "min_occurs", 1)
                            max_occurs = getattr(child_elem, "max_occurs", 1)

                            if not include_optional and min_occurs == 0:
                                continue

                            child_info = {
                                "name": child_elem.name,
                                "required": min_occurs > 0,
                                "multiple": max_occurs == "unbounded"
                                or (max_occurs is not None and max_occurs > 1),
                                "min_occurs": min_occurs,
                                "max_occurs": max_occurs,
                                "attributes": [],
                                "children": [],
                                "text_content": None,
                            }

                            if hasattr(child_elem, "type") and child_elem.type:
                                if child_elem.type.is_simple():
                                    child_info["text_content"] = (
                                        self._get_example_value(child_elem.type)
                                    )
                                elif child_elem.type.is_complex():
                                    child_info["children"] = self._get_child_elements(
                                        child_elem.type, include_optional
                                    )

                            children.append(child_info)
        except Exception:
            # Silently handle errors and continue
            pass

        return children

    def _get_example_value(self, type_obj) -> str:
        """Get example value for a type"""
        try:
            # Handle common FEWS types
            type_name = str(type_obj).lower()

            if "date" in type_name:
                return "2024-01-01"
            elif "time" in type_name:
                return "12:00:00"
            elif "datetime" in type_name:
                return "2024-01-01T12:00:00"
            elif "int" in type_name or "integer" in type_name:
                return "1"
            elif (
                "float" in type_name or "double" in type_name or "decimal" in type_name
            ):
                return "1.0"
            elif "boolean" in type_name:
                return "true"
            else:
                return "example_value"
        except Exception:
            return "example_value"

    def _create_xml_template(
        self, structure: Dict[str, Any], schema: xmlschema.XMLSchema
    ) -> str:
        """Create XML template from structure"""
        target_namespace = schema.target_namespace
        namespace_prefix = "fews" if target_namespace else ""

        # Create namespace declaration
        namespace_decl = (
            f'xmlns:{namespace_prefix}="{target_namespace}"' if target_namespace else ""
        )

        # Generate XML content
        xml_content = self._generate_element_xml(structure, namespace_prefix, 0)

        # Extract local name from structure name (remove namespace if present)
        root_element_name = structure["name"]
        if "}" in root_element_name:
            root_element_name = root_element_name.split("}")[-1]

        # Wrap with root element and namespace
        if namespace_decl:
            template = f"<{namespace_prefix}:{root_element_name} {namespace_decl}>\n{xml_content}\n</{namespace_prefix}:{root_element_name}>"
        else:
            template = f"<{root_element_name}>\n{xml_content}\n</{root_element_name}>"

        return template

    def _generate_element_xml(
        self, structure: Dict[str, Any], namespace_prefix: str, indent_level: int
    ) -> str:
        """Generate XML for an element structure"""
        indent = "  " * indent_level

        # Extract local name from element name (remove namespace if present)
        element_name = structure["name"]
        if "}" in element_name:
            element_name = element_name.split("}")[-1]

        # Add namespace prefix if needed
        if namespace_prefix and ":" not in element_name:
            element_name = f"{namespace_prefix}:{element_name}"

        # Add attributes
        attributes = []
        if "attributes" in structure and structure["attributes"]:
            for attr in structure["attributes"]:
                attr_name = attr["name"]
                # Extract local name from attribute name
                if "}" in attr_name:
                    attr_name = attr_name.split("}")[-1]
                if namespace_prefix and ":" not in attr_name:
                    attr_name = f"{namespace_prefix}:{attr_name}"

                if attr["default"]:
                    attributes.append(f'{attr_name}="{attr["default"]}"')
                else:
                    attributes.append(f'{attr_name}="example_value"')

        attr_str = " ".join(attributes)
        start_tag = f"{element_name} {attr_str}".strip()

        # Handle content
        if structure.get("text_content"):
            # Simple element with text content
            return f"{indent}<{start_tag}>{structure['text_content']}</{element_name}>"
        elif structure.get("children"):
            # Complex element with children
            xml_lines = [f"{indent}<{start_tag}>"]

            for child in structure["children"]:
                child_xml = self._generate_element_xml(
                    child, namespace_prefix, indent_level + 1
                )
                xml_lines.append(child_xml)

                # Add multiple instances if needed
                if child.get("multiple", False):
                    child_xml2 = self._generate_element_xml(
                        child, namespace_prefix, indent_level + 1
                    )
                    xml_lines.append(child_xml2)

            xml_lines.append(f"{indent}</{element_name}>")
            return "\n".join(xml_lines)
        else:
            # Empty element
            return f"{indent}<{start_tag}/>"


async def generate_xml_template(ctx, input: XMLTemplateInput) -> XMLTemplateOutput:
    """
    Generate XML template from XSD schema.

    This tool uses xmlschema to analyze XSD schemas and generate
    valid XML templates with proper structure and example values.
    """
    # Get schema cache directory from context
    schemas_dir = ctx.deps.cache_fews_schemas_dir

    # Create generator instance
    generator = XMLTemplateGenerator(schemas_dir)

    # Generate template
    template = await generator.generate_template(
        schema_url=input.schema_url,
        root_element=input.root_element,
        include_optional=input.include_optional,
        include_attributes=input.include_attributes,
    )

    # Determine root element from schema
    schema = await generator._load_schema(input.schema_url)
    root_element = input.root_element
    if not root_element and schema.root_elements:
        root_element = schema.root_elements[0].name
    elif not root_element:
        root_element = "unknown"

    return XMLTemplateOutput(
        template=template,
        schema_location=input.schema_url,
        root_element=root_element,
        includes_optional=input.include_optional,
        includes_attributes=input.include_attributes,
    )
