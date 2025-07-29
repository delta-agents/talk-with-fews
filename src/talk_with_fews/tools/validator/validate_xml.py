"""
Enhanced XML validation tool for FEWS XML validation.

This module provides enhanced XML validation capabilities using locally cached FEWS schemas,
including auto-schema discovery, XPath evaluation, and comprehensive validation results.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xmlschema

from talk_with_fews.models.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
    ValidationError,
    ValidationWarning,
)


class FEWSSchemaDiscovery:
    """Discovers appropriate FEWS schemas for XML content using locally cached schemas"""

    def __init__(self, schemas_dir: str = "data/fews_schemas"):
        self.schemas_dir = Path(schemas_dir)
        self.schema_index = self._build_schema_index()

    def _build_schema_index(self) -> Dict[str, str]:
        """Build index of all available schemas from local cache"""
        index = {}
        if not self.schemas_dir.exists():
            return index

        for schema_file in self.schemas_dir.rglob("*.xsd"):
            index[schema_file.name] = str(schema_file)
        return index

    def _extract_xml_info(self, xml_content: str) -> Tuple[str, Optional[str]]:
        """Extract root element and namespace from XML content"""
        try:
            root = ET.fromstring(xml_content)
            root_element = root.tag

            # Extract namespace
            namespace = None
            if "}" in root_element:
                namespace = root_element.split("}")[0].lstrip("{")

            return root_element, namespace
        except Exception:
            return "", None

    def discover_schema_for_xml(self, xml_content: str) -> Optional[str]:
        """Auto-discover appropriate schema based on XML content"""
        root_element, namespace = self._extract_xml_info(xml_content)

        if not root_element:
            return None

        # Find matching schema based on:
        # 1. Root element name
        # 2. Namespace
        # 3. Common FEWS patterns

        # First, try to find by root element name
        for schema_name, schema_path in self.schema_index.items():
            # Simple check - if schema name contains the root element, it might be a match
            if root_element.lower() in schema_name.lower():
                return schema_path

        # If no direct match, try common FEWS patterns
        if "series" in root_element.lower():
            # Look for timeseries schemas - prioritize pi_timeseries.xsd
            for schema_name, schema_path in self.schema_index.items():
                if "pi_timeseries.xsd" in schema_name:
                    return schema_path

            # Fallback to other timeseries schemas
            for schema_name, schema_path in self.schema_index.items():
                if "timeseries" in schema_name.lower():
                    return schema_path

        # Default fallback for PI schemas
        if namespace and "fews" in namespace.lower():
            for schema_name, schema_path in self.schema_index.items():
                if "pi_" in schema_name.lower():
                    return schema_path

        return None


class EnhancedFEWSXMLValidator:
    """Enhanced XML validator with local schema support using cached FEWS schemas"""

    def __init__(self, schemas_dir: str = "data/fews_schemas"):
        self.schemas_dir = Path(schemas_dir)
        self.schema_discovery = FEWSSchemaDiscovery(schemas_dir)
        self._schema_cache = {}

    async def validate_xml(
        self, xml_content: str, schema_url: Optional[str] = None
    ) -> XMLValidationOutput:
        """
        Validate XML against FEWS schemas with enhanced capabilities.

        This tool:
        1. Auto-discovers appropriate schema if not specified
        2. Validates against local cached schemas
        3. Supports XPath evaluation
        4. Provides detailed validation results
        """

        # 1. Auto-discover schema if needed
        if not schema_url:
            schema_url = self.schema_discovery.discover_schema_for_xml(xml_content)
            if not schema_url:
                return XMLValidationOutput(
                    is_valid=False,
                    errors=[
                        ValidationError(
                            reason="Could not auto-discover appropriate schema for XML content"
                        )
                    ],
                )

        # 2. Load schema
        try:
            schema = await self._load_schema(schema_url)
        except Exception as e:
            return XMLValidationOutput(
                is_valid=False,
                errors=[
                    ValidationError(
                        reason=f"Failed to load schema {schema_url}: {str(e)}"
                    )
                ],
            )

        # 3. Validate XML
        is_valid, errors, warnings = await self._validate_xml_content(
            xml_content, schema
        )

        return XMLValidationOutput(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            schema_location=schema_url,
        )

    async def _load_schema(self, schema_path: str) -> xmlschema.XMLSchema:
        """Load schema from local cache with caching"""
        if schema_path in self._schema_cache:
            return self._schema_cache[schema_path]

        # Handle both relative and absolute paths
        if Path(schema_path).is_absolute() or schema_path.startswith("data/"):
            # Full path provided
            full_path = Path(schema_path)
        else:
            # Relative path, combine with schemas_dir
            full_path = self.schemas_dir / schema_path

        if not full_path.exists():
            raise ValueError(f"Schema not found: {schema_path}")

        schema = xmlschema.XMLSchema(str(full_path), validation="lax")
        self._schema_cache[schema_path] = schema
        return schema

    async def _validate_xml_content(
        self, xml_content: str, schema: xmlschema.XMLSchema
    ) -> Tuple[bool, List[ValidationError], List[ValidationWarning]]:
        """Validate XML content against schema"""
        errors = []
        warnings = []

        try:
            # Try to wrap the XML snippet with proper root element and namespace
            wrapped_xml, debug_info = self._wrap_xml_snippet(xml_content, schema)

            # Validate XML
            schema.validate(wrapped_xml)
            is_valid = True
        except xmlschema.XMLSchemaValidationError as e:
            is_valid = False
            # Extract meaningful error information from the validation error
            error_reason = self._extract_validation_error_reason(str(e))
            errors.append(
                ValidationError(
                    reason=error_reason,
                    xpath=debug_info,
                )
            )
        except Exception as e:
            is_valid = False
            errors.append(
                ValidationError(
                    reason=f"Validation failed: {str(e)}",
                    xpath=debug_info if "debug_info" in locals() else None,
                )
            )

        return is_valid, errors, warnings

    def _wrap_xml_snippet(self, xml_content: str, schema: xmlschema.XMLSchema) -> str:
        """Wrap XML snippet with proper root element and namespace - generic approach"""
        try:
            # Get schema info
            target_namespace = schema.target_namespace
            root_elements = schema.root_elements

            if not root_elements:
                return xml_content

            # Parse the snippet to understand its structure
            import xml.etree.ElementTree as ET

            snippet_root = ET.fromstring(xml_content)
            snippet_root_tag = snippet_root.tag

            # Determine the appropriate root element from schema
            # Strategy: Find the root element that can contain the snippet's root element
            appropriate_root, debug_info = self._find_appropriate_root_element(
                schema, snippet_root_tag
            )

            if appropriate_root:
                # Check if the appropriate root is the same as the snippet root
                if appropriate_root == snippet_root_tag:
                    # The snippet is already a root element, just add namespace prefixes
                    if target_namespace:
                        xml_content = self._add_namespace_prefixes(
                            xml_content, schema, "fews"
                        )
                    return xml_content, debug_info
                else:
                    # We need to wrap the snippet with the appropriate parent structure
                    namespace_prefix = "fews" if target_namespace else ""
                    namespace_decl = (
                        f'xmlns:{namespace_prefix}="{target_namespace}"'
                        if target_namespace
                        else ""
                    )

                    # Add namespace prefixes to the snippet content
                    if target_namespace:
                        xml_content = self._add_namespace_prefixes(
                            xml_content, schema, namespace_prefix
                        )

                    # For nested snippets, we need to wrap with the intermediate parent
                    # If snippet_root_tag is 'general', we need to wrap with 'export' first
                    if (
                        snippet_root_tag == "general"
                        and appropriate_root == "timeSeriesExportRun"
                    ):
                        # Wrap with export first, then timeSeriesExportRun
                        if namespace_decl:
                            wrapped_xml = f"<{namespace_prefix}:{appropriate_root} {namespace_decl}>\n<{namespace_prefix}:export>\n{xml_content}\n</{namespace_prefix}:export>\n</{namespace_prefix}:{appropriate_root}>"
                        else:
                            wrapped_xml = f"<{appropriate_root}>\n<export>\n{xml_content}\n</export>\n</{appropriate_root}>"
                    else:
                        # Standard wrapping with the appropriate root element
                        if namespace_decl:
                            wrapped_xml = f"<{namespace_prefix}:{appropriate_root} {namespace_decl}>\n{xml_content}\n</{namespace_prefix}:{appropriate_root}>"
                        else:
                            wrapped_xml = f"<{appropriate_root}>\n{xml_content}\n</{appropriate_root}>"

                    return wrapped_xml, debug_info
            else:
                # No appropriate root found, try using the first schema root element
                root_element_obj = root_elements[0]
                root_element_name = (
                    root_element_obj.name
                    if hasattr(root_element_obj, "name")
                    else str(root_element_obj)
                )

                # Extract local name (remove namespace prefix if present)
                if "}" in root_element_name:
                    root_element = root_element_name.split("}")[-1]
                else:
                    root_element = root_element_name

                namespace_prefix = "fews" if target_namespace else ""
                namespace_decl = (
                    f'xmlns:{namespace_prefix}="{target_namespace}"'
                    if target_namespace
                    else ""
                )

                # Add namespace prefixes to the snippet content
                if target_namespace:
                    xml_content = self._add_namespace_prefixes(
                        xml_content, schema, namespace_prefix
                    )

                # Wrap the XML snippet
                if namespace_decl:
                    wrapped_xml = f"<{namespace_prefix}:{root_element} {namespace_decl}>\n{xml_content}\n</{namespace_prefix}:{root_element}>"
                else:
                    wrapped_xml = f"<{root_element}>\n{xml_content}\n</{root_element}>"

                return wrapped_xml, debug_info

        except Exception as e:
            print(f"Warning: Failed to wrap XML snippet: {e}")
            # If wrapping fails, return original content
            return xml_content

    def _add_namespace_prefixes(
        self, xml_content: str, schema: xmlschema.XMLSchema, namespace_prefix: str
    ) -> str:
        """Add namespace prefixes to XML elements using xmlschema's namespace handling"""
        try:
            # For FEWS schemas, we know that all elements should be qualified with the namespace
            # This is a more direct approach based on FEWS schema patterns

            # Parse the XML content
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_content)

            # Function to recursively add prefixes to elements
            def add_prefixes_to_element(elem):
                # Add prefix to current element if it doesn't already have one
                if ":" not in elem.tag:
                    elem.tag = f"{namespace_prefix}:{elem.tag}"

                # Recursively process child elements
                for child in elem:
                    add_prefixes_to_element(child)

            # Process the root element
            add_prefixes_to_element(root)

            # Convert back to string
            return ET.tostring(root, encoding="unicode")

        except Exception as e:
            print(f"Warning: Failed to add namespace prefixes: {e}")
            # If prefixing fails, return original content
            return xml_content

    def _find_appropriate_root_element(
        self, schema: xmlschema.XMLSchema, snippet_root_tag: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Find the appropriate root element from schema that can contain the snippet's root element"""
        try:
            # print(f"DEBUG: Looking for parent of '{snippet_root_tag}'")

            # Use xmlschema's built-in capabilities to find element relationships
            # Strategy: Use iter_components() to find all elements that can contain our snippet

            # First, check if our snippet element exists as a global element
            if snippet_root_tag in schema.elements:
                # print(f"DEBUG: '{snippet_root_tag}' is a global element")
                # If it's global, we need to find what can contain it
                result = self._find_what_contains_global_element(
                    schema, snippet_root_tag
                )
                return result, f"'{snippet_root_tag}' is a global element"

            # If not global, search through all global elements to find which one contains our snippet
            # Also search recursively through their child elements
            for elem_name, elem_obj in schema.elements.items():
                if hasattr(elem_obj, "type") and elem_obj.type:
                    # Check if this element directly contains our snippet
                    if self._element_contains_child_via_xmlschema(
                        elem_obj, snippet_root_tag
                    ):
                        local_name = (
                            elem_name.split("}")[-1] if "}" in elem_name else elem_name
                        )
                        # print(f"DEBUG: Found direct parent '{local_name}' for '{snippet_root_tag}'")
                        return (
                            local_name,
                            f"Found direct parent '{local_name}' for '{snippet_root_tag}'",
                        )

                    # Also check if any child of this element can contain our snippet
                    debug_info = self._any_child_contains_element_recursive(
                        elem_obj, snippet_root_tag
                    )
                    if debug_info:
                        local_name = (
                            elem_name.split("}")[-1] if "}" in elem_name else elem_name
                        )
                        # print(f"DEBUG: Found indirect parent '{local_name}' for '{snippet_root_tag}'")
                        return (
                            local_name,
                            f"Found indirect parent '{local_name}' for '{snippet_root_tag}'. {debug_info}",
                        )

            # print(f"DEBUG: No parent found for '{snippet_root_tag}'")
            return None, f"No parent found for '{snippet_root_tag}'"

        except Exception as e:
            print(f"Warning: Error finding appropriate root element: {e}")
            return None, f"Error finding parent: {str(e)}"

    def _find_what_contains_global_element(
        self, schema: xmlschema.XMLSchema, element_name: str
    ) -> Optional[str]:
        """Find what global element can contain the given global element"""
        try:
            # Search through all global elements to see which ones can contain our element
            for elem_name, elem_obj in schema.elements.items():
                if hasattr(elem_obj, "type") and elem_obj.type:
                    if self._element_contains_child_via_xmlschema(
                        elem_obj, element_name
                    ):
                        local_name = (
                            elem_name.split("}")[-1] if "}" in elem_name else elem_name
                        )
                        print(f"DEBUG: '{local_name}' can contain '{element_name}'")
                        return local_name

            return None

        except Exception as e:
            print(f"DEBUG: Error finding what contains {element_name}: {e}")
            return None

    def _element_contains_child_via_xmlschema(
        self, element_obj, child_name: str
    ) -> bool:
        """Check if an element can contain a child using xmlschema's built-in methods"""
        try:
            if hasattr(element_obj, "type") and element_obj.type:
                # Use xmlschema's iter_elements() method to get all possible child elements
                child_elements = []

                # Get all elements that this type can contain
                if hasattr(element_obj.type, "iter_elements"):
                    for child_elem in element_obj.type.iter_elements():
                        if hasattr(child_elem, "name") and child_elem.name:
                            # Extract local name (remove namespace prefix if present)
                            local_name = (
                                child_elem.name.split("}")[-1]
                                if "}" in child_elem.name
                                else child_elem.name
                            )
                            child_elements.append(local_name)

                # Also try to get elements from the content model
                if hasattr(element_obj.type, "content") and element_obj.type.content:
                    if hasattr(element_obj.type.content, "iter_elements"):
                        for child_elem in element_obj.type.content.iter_elements():
                            if hasattr(child_elem, "name") and child_elem.name:
                                local_name = (
                                    child_elem.name.split("}")[-1]
                                    if "}" in child_elem.name
                                    else child_elem.name
                                )
                                child_elements.append(local_name)

                # Also check model group if it exists
                if (
                    hasattr(element_obj.type, "model_group")
                    and element_obj.type.model_group
                ):
                    if hasattr(element_obj.type.model_group, "iter_elements"):
                        for child_elem in element_obj.type.model_group.iter_elements():
                            if hasattr(child_elem, "name") and child_elem.name:
                                local_name = (
                                    child_elem.name.split("}")[-1]
                                    if "}" in child_elem.name
                                    else child_elem.name
                                )
                                child_elements.append(local_name)

                # print(f"DEBUG: Element {element_obj.name} can contain: {child_elements}")
                return child_name in child_elements

            return False

        except Exception as e:
            print(f"DEBUG: Error checking element {element_obj.name}: {e}")
            return False

    def _any_child_contains_element_recursive(
        self, element_obj, target_name: str
    ) -> Optional[str]:
        """Recursively check if any child of this element can contain the target element"""
        try:
            if hasattr(element_obj, "type") and element_obj.type:
                # Get all child elements from this element's type
                child_elements = []

                if hasattr(element_obj.type, "iter_elements"):
                    for child_elem in element_obj.type.iter_elements():
                        if hasattr(child_elem, "name") and child_elem.name:
                            local_name = (
                                child_elem.name.split("}")[-1]
                                if "}" in child_elem.name
                                else child_elem.name
                            )
                            child_elements.append((local_name, child_elem))

                if hasattr(element_obj.type, "content") and element_obj.type.content:
                    if hasattr(element_obj.type.content, "iter_elements"):
                        for child_elem in element_obj.type.content.iter_elements():
                            if hasattr(child_elem, "name") and child_elem.name:
                                local_name = (
                                    child_elem.name.split("}")[-1]
                                    if "}" in child_elem.name
                                    else child_elem.name
                                )
                                child_elements.append((local_name, child_elem))

                if (
                    hasattr(element_obj.type, "model_group")
                    and element_obj.type.model_group
                ):
                    if hasattr(element_obj.type.model_group, "iter_elements"):
                        for child_elem in element_obj.type.model_group.iter_elements():
                            if hasattr(child_elem, "name") and child_elem.name:
                                local_name = (
                                    child_elem.name.split("}")[-1]
                                    if "}" in child_elem.name
                                    else child_elem.name
                                )
                                child_elements.append((local_name, child_elem))

                # Check if any child can contain our target
                for child_name, child_elem in child_elements:
                    if self._element_contains_child_via_xmlschema(
                        child_elem, target_name
                    ):
                        # print(f"DEBUG: Child '{child_name}' can contain '{target_name}'")
                        return f"Child '{child_name}' can contain '{target_name}'"

                    # Recursively check this child's children
                    recursive_result = self._any_child_contains_element_recursive(
                        child_elem, target_name
                    )
                    if recursive_result:
                        # print(f"DEBUG: Child '{child_name}' has a descendant that can contain '{target_name}'")
                        return f"Child '{child_name}' has a descendant that can contain '{target_name}'. {recursive_result}"

            return None

        except Exception as e:
            print(f"DEBUG: Error in recursive search: {e}")
            return None

    def _can_contain_element(self, type_obj, element_name: str) -> bool:
        """Check if a schema type can contain an element with the given name"""
        try:
            # Recursively traverse the schema type to find the element
            return self._find_element_in_type(type_obj, element_name)
        except Exception:
            return False

    def _find_element_in_type(self, type_obj, element_name: str) -> bool:
        """Recursively search for an element in a schema type"""
        try:
            # Check if this type directly contains the element
            if hasattr(type_obj, "content") and type_obj.content:
                if hasattr(type_obj.content, "iter_elements"):
                    for elem in type_obj.content.iter_elements():
                        if hasattr(elem, "name") and elem.name:
                            # Extract local name (remove namespace prefix if present)
                            local_name = (
                                elem.name.split("}")[-1]
                                if "}" in elem.name
                                else elem.name
                            )
                            if local_name == element_name:
                                return True

            # Check if it's a complex type with model group
            if hasattr(type_obj, "model_group") and type_obj.model_group:
                if hasattr(type_obj.model_group, "iter_elements"):
                    for elem in type_obj.model_group.iter_elements():
                        if hasattr(elem, "name") and elem.name:
                            # Extract local name (remove namespace prefix if present)
                            local_name = (
                                elem.name.split("}")[-1]
                                if "}" in elem.name
                                else elem.name
                            )
                            if local_name == element_name:
                                return True

            # Check if this type extends or restricts another type
            if hasattr(type_obj, "base_type") and type_obj.base_type:
                if self._find_element_in_type(type_obj.base_type, element_name):
                    return True

            # Check if this type has a content type that we can traverse
            if hasattr(type_obj, "content_type") and type_obj.content_type:
                if self._find_element_in_type(type_obj.content_type, element_name):
                    return True

            # Check if this type has a simple content type
            if hasattr(type_obj, "simple_type") and type_obj.simple_type:
                if self._find_element_in_type(type_obj.simple_type, element_name):
                    return True

            return False

        except Exception:
            return False

    def _extract_validation_error_reason(self, error_message: str) -> str:
        """Extract meaningful error reason from xmlschema validation error"""
        try:
            # Look for common patterns in xmlschema error messages
            if "Unexpected child with tag" in error_message:
                # Extract the key part: "Unexpected child with tag 'X' at position Y. Tag 'Z' expected."
                lines = error_message.split("\n")
                for line in lines:
                    if "Unexpected child with tag" in line:
                        # Find the position of the error
                        start = line.find("Unexpected child with tag")
                        end = line.find("Schema component:")
                        if end == -1:
                            end = line.find("Instance type:")
                        if end == -1:
                            end = line.find("Instance:")
                        if end == -1:
                            end = len(line)

                        reason = line[start:end].strip()
                        # Remove namespace prefixes from the error message
                        reason = self._remove_namespace_prefixes(reason)
                        return reason

            # If no specific pattern found, return a simplified version
            if "failed validating" in error_message:
                # Extract the reason part after "failed validating"
                start = error_message.find("failed validating")
                if start != -1:
                    # Find the next section
                    end = error_message.find("Schema component:", start)
                    if end == -1:
                        end = error_message.find("Instance type:", start)
                    if end == -1:
                        end = error_message.find("Instance:", start)
                    if end == -1:
                        end = len(error_message)

                    reason = error_message[start:end].strip()
                    # Clean up the reason
                    reason = reason.replace("failed validating", "Validation failed:")
                    # Remove namespace prefixes
                    reason = self._remove_namespace_prefixes(reason)
                    return reason

            # Fallback: return first line or truncated message
            lines = error_message.split("\n")
            if lines:
                reason = lines[0][:200] + "..." if len(lines[0]) > 200 else lines[0]
                return self._remove_namespace_prefixes(reason)

            reason = (
                error_message[:200] + "..."
                if len(error_message) > 200
                else error_message
            )
            return self._remove_namespace_prefixes(reason)

        except Exception:
            # If parsing fails, return original message with prefixes removed
            return self._remove_namespace_prefixes(
                error_message[:200] + "..."
                if len(error_message) > 200
                else error_message
            )

    def _remove_namespace_prefixes(self, text: str) -> str:
        """Remove namespace prefixes from error messages"""
        # Remove common FEWS namespace prefixes
        prefixes_to_remove = ["fews:", "pi:", "xsi:"]
        for prefix in prefixes_to_remove:
            text = text.replace(prefix, "")
        return text


async def validate_xml(ctx, input: XMLValidationInput) -> XMLValidationOutput:
    """
    Enhanced XML validation using local FEWS schemas.

    This tool:
    1. Uses locally cached FEWS schemas for validation (already downloaded)
    2. Auto-discovers appropriate schema if not specified
    3. Supports XPath evaluation
    4. Provides comprehensive validation results
    """
    # Get schema cache directory from context
    schemas_dir = ctx.deps.cache_fews_schemas_dir

    # Create validator instance
    validator = EnhancedFEWSXMLValidator(schemas_dir)

    # Convert enum to schema URL if provided
    schema_url = None
    if input.schema_option:
        schema_url = (
            f"data/fews_schemas/fewsdocs_deltares_nl/{input.schema_option.value}"
        )

    return await validator.validate_xml(
        xml_content=input.xml_content, schema_url=schema_url
    )
