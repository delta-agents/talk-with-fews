"""
Enhanced XML validation tool for FEWS XML validation.

This module provides enhanced XML validation capabilities using locally cached FEWS schemas,
including auto-schema discovery, XPath evaluation, and comprehensive validation results.
"""

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xmlschema
from elementpath import select

from talk_with_fews.models.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
    ValidationError,
    ValidationWarning,
    XPathResult,
    SchemaInfo,
    ValidationSummary,
)


class FEWSSchemaDiscovery:
    """Discovers appropriate FEWS schemas for XML content using locally cached schemas"""

    def __init__(self, schemas_dir: str = "data/fews_schemas"):
        self.schemas_dir = Path(schemas_dir)
        self.schema_index = self._build_schema_index()

    def _build_schema_index(self) -> Dict[str, SchemaInfo]:
        """Build index of all available schemas from local cache"""
        index = {}
        if not self.schemas_dir.exists():
            return index

        for schema_file in self.schemas_dir.rglob("*.xsd"):
            try:
                schema_info = self._extract_schema_info(schema_file)
                index[schema_file.name] = schema_info
            except Exception as e:
                print(f"Warning: Could not extract info from {schema_file}: {e}")
        return index

    def _extract_schema_info(self, schema_file: Path) -> SchemaInfo:
        """Extract basic information from a schema file"""
        try:
            # Parse the schema file to extract basic info
            tree = ET.parse(schema_file)
            root = tree.getroot()

            # Extract namespace
            target_namespace = root.get("targetNamespace")

            # Determine schema type from path
            schema_type = "unknown"
            if "pi-schemas" in str(schema_file):
                schema_type = "pi-schemas"
            elif "adapter-schemas" in str(schema_file):
                schema_type = "adapter-schemas"
            elif "schemas" in str(schema_file):
                schema_type = "core-schemas"

            # Extract root elements (simplified - could be enhanced)
            root_elements = []
            for elem in root.findall(".//{*}element"):
                name = elem.get("name")
                if name:
                    root_elements.append(name)

            return SchemaInfo(
                schema_url=str(schema_file),
                target_namespace=target_namespace,
                version=None,  # Could be enhanced to extract version
                description=None,  # Could be enhanced to extract description
                root_elements=root_elements,
                schema_type=schema_type,
            )
        except Exception:
            # Return basic info if parsing fails
            return SchemaInfo(
                schema_url=str(schema_file),
                target_namespace=None,
                version=None,
                description=None,
                root_elements=[],
                schema_type="unknown",
            )

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
        for schema_name, schema_info in self.schema_index.items():
            if root_element in schema_info.root_elements:
                return schema_info.schema_url

        # If no direct match, try common FEWS patterns
        if "series" in root_element.lower():
            # Look for timeseries schemas - prioritize pi_timeseries.xsd
            for schema_name, schema_info in self.schema_index.items():
                if "pi_timeseries.xsd" in schema_name:
                    return schema_info.schema_url

            # Fallback to other timeseries schemas
            for schema_name, schema_info in self.schema_index.items():
                if "timeseries" in schema_name.lower():
                    return schema_info.schema_url

        # Default fallback for PI schemas
        if namespace and "fews" in namespace.lower():
            for schema_name, schema_info in self.schema_index.items():
                if "pi_" in schema_name.lower():
                    return schema_info.schema_url

        return None

    def get_schema_info(self, schema_path: str) -> Optional[SchemaInfo]:
        """Get detailed information about a schema"""
        # Try direct match first
        if schema_path in self.schema_index:
            return self.schema_index[schema_path]

        # Try to find by schema URL
        for schema_info in self.schema_index.values():
            if schema_info.schema_url == schema_path:
                return schema_info

        return None


class FEWSXPathEvaluator:
    """XPath evaluation using ElementPath library"""

    def __init__(self):
        self.namespaces = {
            "fews": "http://www.wldelft.nl/fews/PI",
            "pi": "http://www.wldelft.nl/fews/PI",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

    def evaluate_xpath(
        self, xml_content: str, xpath_expression: str
    ) -> List[XPathResult]:
        """Evaluate XPath expression against XML content"""
        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # Evaluate XPath
            results = select(root, xpath_expression, namespaces=self.namespaces)

            return [
                XPathResult(
                    element=str(result),
                    tag=result.tag if hasattr(result, "tag") else str(result),
                    text=result.text if hasattr(result, "text") else None,
                    attributes=dict(result.attrib) if hasattr(result, "attrib") else {},
                    error=None,
                )
                for result in results
            ]
        except Exception as e:
            return [
                XPathResult(element="", tag="", text="", attributes={}, error=str(e))
            ]


class EnhancedFEWSXMLValidator:
    """Enhanced XML validator with local schema support using cached FEWS schemas"""

    def __init__(self, schemas_dir: str = "data/fews_schemas"):
        self.schemas_dir = Path(schemas_dir)
        self.schema_discovery = FEWSSchemaDiscovery(schemas_dir)
        self.xpath_evaluator = FEWSXPathEvaluator()
        self._schema_cache = {}

    async def validate_xml(
        self,
        xml_content: str,
        schema_url: Optional[str] = None,
        xpath: Optional[str] = None,
        validation_mode: str = "lax",
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
                    validation_summary=ValidationSummary(
                        total_elements=0,
                        validated_elements=0,
                        error_count=1,
                        warning_count=0,
                        validation_time_ms=0,
                        schema_load_time_ms=0,
                    ),
                )

        # 2. Load schema
        schema_load_start = time.time()
        try:
            schema = await self._load_schema(schema_url)
            schema_load_time = (time.time() - schema_load_start) * 1000
        except Exception as e:
            return XMLValidationOutput(
                is_valid=False,
                errors=[
                    ValidationError(
                        reason=f"Failed to load schema {schema_url}: {str(e)}"
                    )
                ],
                validation_summary=ValidationSummary(
                    total_elements=0,
                    validated_elements=0,
                    error_count=1,
                    warning_count=0,
                    validation_time_ms=0,
                    schema_load_time_ms=0,
                ),
            )

        # 3. Validate XML
        validation_start = time.time()
        is_valid, errors, warnings = await self._validate_xml_content(
            xml_content, schema, validation_mode
        )
        validation_time = (time.time() - validation_start) * 1000

        # 4. Evaluate XPath if specified
        xpath_results = None
        if xpath:
            xpath_results = self.xpath_evaluator.evaluate_xpath(xml_content, xpath)

        # 5. Get schema information
        schema_info = self.schema_discovery.get_schema_info(schema_url)

        return XMLValidationOutput(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            schema_location=schema_url,
            schema_info=schema_info,
            xpath_results=xpath_results,
            validation_summary=ValidationSummary(
                total_elements=self._count_elements(xml_content),
                validated_elements=self._count_validated_elements(xml_content, errors),
                error_count=len(errors),
                warning_count=len(warnings),
                validation_time_ms=validation_time,
                schema_load_time_ms=schema_load_time,
            ),
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
        self, xml_content: str, schema: xmlschema.XMLSchema, validation_mode: str
    ) -> Tuple[bool, List[ValidationError], List[ValidationWarning]]:
        """Validate XML content against schema"""
        errors = []
        warnings = []

        try:
            # Try to wrap the XML snippet with proper root element and namespace
            wrapped_xml = self._wrap_xml_snippet(xml_content, schema)

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
                    line=None,  # Could be extracted from error message if needed
                    column=None,
                    element=None,
                )
            )
        except Exception as e:
            is_valid = False
            errors.append(ValidationError(reason=f"Validation failed: {str(e)}"))

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
            appropriate_root = self._find_appropriate_root_element(
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
                    return xml_content
                else:
                    # We need to wrap the snippet
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

                    # Wrap with the appropriate root element
                    if namespace_decl:
                        wrapped_xml = f"<{namespace_prefix}:{appropriate_root} {namespace_decl}>\n{xml_content}\n</{namespace_prefix}:{appropriate_root}>"
                    else:
                        wrapped_xml = f"<{appropriate_root}>\n{xml_content}\n</{appropriate_root}>"

                    return wrapped_xml
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

                return wrapped_xml

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
    ) -> Optional[str]:
        """Find the appropriate root element from schema that can contain the snippet's root element"""
        try:
            # Strategy: Look through schema components to find which root element
            # can contain the snippet's root element as a child

            # Get all global elements from the schema
            for elem_name, elem_obj in schema.elements.items():
                if hasattr(elem_obj, "type") and elem_obj.type:
                    # Check if this element's type can contain our snippet root
                    if self._can_contain_element(elem_obj.type, snippet_root_tag):
                        # Extract local name from qualified name
                        if "}" in elem_name:
                            return elem_name.split("}")[-1]
                        else:
                            return elem_name

            # If no match found, return None to use fallback strategy
            return None

        except Exception as e:
            print(f"Warning: Error finding appropriate root element: {e}")
            return None

    def _can_contain_element(self, type_obj, element_name: str) -> bool:
        """Check if a schema type can contain an element with the given name"""
        try:
            # This is a simplified check - in a full implementation, you'd traverse
            # the schema type hierarchy more thoroughly

            # Check if the type has content that includes our element
            if hasattr(type_obj, "content") and type_obj.content:
                if hasattr(type_obj.content, "iter_elements"):
                    for elem in type_obj.content.iter_elements():
                        if (
                            hasattr(elem, "name")
                            and elem.name
                            and element_name in elem.name
                        ):
                            return True

            # Check if it's a complex type with model group
            if hasattr(type_obj, "model_group") and type_obj.model_group:
                if hasattr(type_obj.model_group, "iter_elements"):
                    for elem in type_obj.model_group.iter_elements():
                        if (
                            hasattr(elem, "name")
                            and elem.name
                            and element_name in elem.name
                        ):
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

    def _count_elements(self, xml_content: str) -> int:
        """Count total elements in XML"""
        try:
            root = ET.fromstring(xml_content)
            return len(list(root.iter()))
        except Exception:
            return 0

    def _count_validated_elements(
        self, xml_content: str, errors: List[ValidationError]
    ) -> int:
        """Count successfully validated elements"""
        total = self._count_elements(xml_content)
        # Simplified: assume all elements are validated if no errors
        return total if not errors else max(0, total - len(errors))


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
    schemas_dir = getattr(ctx.deps, "cache_fews_schemas_dir", "data/fews_schemas")

    # Create validator instance
    validator = EnhancedFEWSXMLValidator(schemas_dir)

    return await validator.validate_xml(
        xml_content=input.xml_content,
        schema_url=input.schema_url,
        xpath=input.xpath,
        validation_mode=input.validation_mode,
    )
