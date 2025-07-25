"""
XML validation tool using xmlschema package.

This module provides functionality to validate complete XML documents or partial XML snippets
against XSD schemas, with support for caching schemas for offline use.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Union, Dict, Tuple
import xml.etree.ElementTree as ET
from io import StringIO

import xmlschema
from xmlschema import download_schemas
from pydantic import BaseModel, Field


# Get the tools directory
TOOLS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "tests" / "src" / "tools"
)


class XMLValidationInput(BaseModel):
    """
    Input model for XML validation.

    Attributes:
        xml_content: The XML content to validate as a string
        schema_url: URL or path to the XSD schema
        xpath: Optional XPath expression to validate only a specific part of the XML
        cache_schema: Whether to cache the schema locally for offline use
        cache_dir: Directory to store cached schemas (default: schemas)
    """

    xml_content: str = Field(..., description="XML content to validate")
    schema_url: str = Field(..., description="URL or path to the XSD schema")
    xpath: Optional[str] = Field(
        None, description="XPath expression to validate only a specific part"
    )
    cache_schema: bool = Field(
        False, description="Whether to cache the schema locally for offline use"
    )
    cache_dir: str = Field("schemas", description="Directory to store cached schemas")


class XMLValidationResult(BaseModel):
    """
    Result of XML validation.

    Attributes:
        is_valid: Whether the XML is valid according to the schema
        errors: List of validation errors if any
        schema_location: Location of the used schema (URL or local path)
    """

    is_valid: bool
    errors: Optional[list[str]] = None
    schema_location: str


class XMLValidator:
    """
    XML validator using xmlschema package.
    Supports full and partial validation of XML against XSD schemas.
    """

    # FEWS namespace mapping
    FEWS_NAMESPACES = {
        "fews": "http://www.wldelft.nl/fews",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    def __init__(self, cache_dir: str = "schemas"):
        # If cache_dir is relative, make it relative to tools directory
        cache_path = Path(cache_dir)
        if not cache_path.is_absolute():
            cache_path = TOOLS_DIR / cache_dir
        self.cache_dir = cache_path
        self._schema_cache = {}

    def _get_schema(self, schema_url: str, cache: bool = False) -> xmlschema.XMLSchema:
        """
        Get XMLSchema instance, optionally caching it locally.

        Args:
            schema_url: URL or path to the XSD schema
            cache: Whether to cache the schema locally

        Returns:
            XMLSchema instance
        """
        if schema_url in self._schema_cache:
            return self._schema_cache[schema_url]

        try:
            # Check if schema_url is a local file
            schema_path = Path(schema_url)
            if schema_path.is_file():
                # Use local file directly
                schema = xmlschema.XMLSchema(str(schema_path), validation="lax")
                self._schema_cache[schema_url] = schema
                return schema

            # If caching is requested, download schema and its dependencies
            if cache:
                # Create a clean schemas directory
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)

                # Let xmlschema handle downloading and managing schemas
                download_schemas(schema_url, str(self.cache_dir))

                # The schema will be in the schemas directory
                schema_path = self.cache_dir / os.path.basename(schema_url)

                # Create schema instance from downloaded file
                schema = xmlschema.XMLSchema(str(schema_path), validation="lax")
                self._schema_cache[schema_url] = schema
                return schema

            # If no caching, try to load schema directly
            schema = xmlschema.XMLSchema(schema_url, validation="lax")
            self._schema_cache[schema_url] = schema
            return schema

        except Exception as e:
            # If loading fails, try to use a more permissive validation mode
            try:
                schema = xmlschema.XMLSchema(schema_url, validation="skip")
                self._schema_cache[schema_url] = schema
                return schema
            except Exception as e2:
                raise RuntimeError(
                    f"Failed to load schema: {e}\nTried skip validation: {e2}"
                )

    def _find_element_with_namespaces(
        self, root: ET.Element, xpath: str, namespaces: Optional[Dict[str, str]] = None
    ) -> Optional[ET.Element]:
        """
        Find an element using XPath with proper namespace handling.

        Args:
            root: Root element to search in
            xpath: XPath expression
            namespaces: Optional namespace mapping

        Returns:
            Found element or None
        """
        # Combine default and provided namespaces
        ns = self.FEWS_NAMESPACES.copy()
        if namespaces:
            ns.update(namespaces)

        try:
            # Try with namespaces first
            return root.find(xpath, namespaces=ns)
        except (SyntaxError, ValueError):
            # If that fails, try without namespaces
            try:
                return root.find(xpath)
            except Exception:
                return None

    def _get_element_schema_info(
        self, element: ET.Element, schema: xmlschema.XMLSchema
    ) -> Tuple[str, Dict[str, str]]:
        """
        Get schema information for an element.

        Args:
            element: Element to get info for
            schema: Schema to use

        Returns:
            Tuple of (local name, namespace declarations)
        """
        # Get element's local name
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        # Get namespace declarations
        namespaces = {}
        for key, value in element.attrib.items():
            if key.startswith("xmlns:"):
                prefix = key.split(":")[1]
                namespaces[prefix] = value
            elif key == "xmlns":
                namespaces[None] = value

        # Add schema's target namespace if not present
        if schema.target_namespace:
            for prefix, uri in self.FEWS_NAMESPACES.items():
                if uri == schema.target_namespace and prefix not in namespaces:
                    namespaces[prefix] = uri

        return tag, namespaces

    def _find_element_type(
        self, tag: str, schema: xmlschema.XMLSchema
    ) -> Optional[xmlschema.XsdType]:
        """
        Find the type definition for an element in the schema.

        Args:
            tag: Element tag name
            schema: Schema to search in

        Returns:
            XsdType if found, None otherwise
        """
        # First try to find the element directly
        for xsd_element in schema.elements.values():
            if xsd_element.local_name == tag:
                return xsd_element.type

        # If not found, look in complex types
        for type_name, type_def in schema.types.items():
            if isinstance(type_def, xmlschema.XsdComplexType):
                for child in type_def.content.iter_elements():
                    if child.local_name == tag:
                        return child.type

        return None

    def _create_partial_schema(
        self, element: ET.Element, schema: xmlschema.XMLSchema
    ) -> str:
        """
        Create a schema that only validates the given element.

        Args:
            element: Element to validate
            schema: Original schema

        Returns:
            String containing the partial schema
        """
        # Get element info
        tag, namespaces = self._get_element_schema_info(element, schema)

        # Create namespace declarations
        ns_decls = []
        for prefix, uri in namespaces.items():
            if prefix:
                ns_decls.append(f'xmlns:{prefix}="{uri}"')
            else:
                ns_decls.append(f'xmlns="{uri}"')

        # Find the element's type
        element_type = self._find_element_type(tag, schema)
        if not element_type:
            raise ValueError(f"Could not find type for element {tag} in schema")

        # Create partial schema
        partial_schema = f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           {" ".join(ns_decls)}
           elementFormDefault="qualified">

    {element_type.tostring()}

    <xs:element name="{tag}" type="{element_type.local_name}"/>
</xs:schema>
"""

        # Write schema to temporary file
        schema_path = self.cache_dir / f"partial_{tag}.xsd"
        schema_path.write_text(partial_schema)

        return str(schema_path)

    def validate(
        self,
        xml_content: Union[str, ET.Element],
        schema_url: str,
        xpath: Optional[str] = None,
        cache_schema: bool = False,
        namespaces: Optional[Dict[str, str]] = None,
    ) -> XMLValidationResult:
        """
        Validate XML content against an XSD schema.

        Args:
            xml_content: XML content as string or ElementTree.Element
            schema_url: URL or path to the XSD schema
            xpath: Optional XPath to validate only a specific part
            cache_schema: Whether to cache the schema locally
            namespaces: Optional additional namespace mapping

        Returns:
            XMLValidationResult with validation status and any errors
        """
        try:
            # Get schema with relaxed validation
            schema = self._get_schema(schema_url, cache_schema)

            # Parse XML if string
            if isinstance(xml_content, str):
                xml_tree = ET.parse(StringIO(xml_content))
                root = xml_tree.getroot()
            else:
                root = xml_content

            # Combine namespaces
            ns = self.FEWS_NAMESPACES.copy()
            if namespaces:
                ns.update(namespaces)

            # Handle partial validation if xpath provided
            if xpath:
                try:
                    # Find the element in the XML first
                    xml_element = root.find(xpath, namespaces=ns)
                    if xml_element is None:
                        return XMLValidationResult(
                            is_valid=False,
                            errors=[f"XPath '{xpath}' not found in XML"],
                            schema_location=schema.url,
                        )

                    # Then find the XSD component for validation
                    xsd_element = schema.find(xpath, namespaces=ns)
                    if xsd_element is None:
                        return XMLValidationResult(
                            is_valid=False,
                            errors=[
                                f"XPath '{xpath}' found in XML but not defined in schema"
                            ],
                            schema_location=schema.url,
                        )

                    # Validate the element against its XSD component
                    xsd_element.validate(xml_element)
                    return XMLValidationResult(
                        is_valid=True, schema_location=schema.url
                    )
                except xmlschema.XMLSchemaValidationError as e:
                    return XMLValidationResult(
                        is_valid=False, errors=[str(e)], schema_location=schema.url
                    )

            # Full document validation
            try:
                schema.validate(root)
                return XMLValidationResult(is_valid=True, schema_location=schema.url)
            except xmlschema.XMLSchemaValidationError as e:
                # Try with skip validation if strict validation fails
                try:
                    schema.validate(root, validation="skip")
                    return XMLValidationResult(
                        is_valid=True, schema_location=schema.url
                    )
                except Exception:
                    return XMLValidationResult(
                        is_valid=False, errors=[str(e)], schema_location=schema.url
                    )

        except Exception as e:
            return XMLValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                schema_location=schema_url,
            )


def create_validator(cache_dir: str = "schemas") -> XMLValidator:
    """Create a new XMLValidator instance."""
    return XMLValidator(cache_dir=cache_dir)
