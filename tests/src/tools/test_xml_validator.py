"""
Tests for the XML validation functionality.

This module tests XML validation against XSD schemas, including full document validation,
partial validation using XPath, and various error cases.
"""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError
from pydantic_ai import RunContext
from pydantic_ai.usage import Usage
from xmlschema import download_schemas
import shutil

from talk_with_fews.tools.validator.validate_xml import validate_xml
from talk_with_fews.tools.validator.xml_validator import XMLValidationInput


# Get the tools directory
TOOLS_DIR = Path(__file__).parent

# FEWS schema URLs
FEWS_SCHEMA_BASE = "https://fewsdocs.deltares.nl/schemas/version1.0"
TIMESERIES_IMPORT_SCHEMA = f"{FEWS_SCHEMA_BASE}/timeSeriesImportRun.xsd"
SHARED_TYPES_SCHEMA = f"{FEWS_SCHEMA_BASE}/sharedTypes.xsd"


@pytest.fixture
def mock_context():
    """Fixture providing a mock RunContext for testing."""
    from talk_with_fews.models.base import Deps

    return RunContext(
        deps=Deps(),
        model="test-model",
        usage=Usage(),
        prompt="test prompt",
        messages=[],
    )


@pytest.fixture
def schema_file(tmp_path):
    """Fixture providing a test schema file."""
    schema_content = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:fews="http://www.wldelft.nl/fews"
               targetNamespace="http://www.wldelft.nl/fews"
               elementFormDefault="qualified"
               attributeFormDefault="unqualified">

        <xs:element name="import">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="general" minOccurs="1" maxOccurs="1">
                        <xs:complexType>
                            <xs:sequence>
                                <xs:element name="importType" type="xs:string"/>
                                <xs:element name="folder" type="xs:string"/>
                                <xs:element name="table">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="dateTimeColumn">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                    <xs:attribute name="pattern" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                            <xs:element name="startDateTimeColumn">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                    <xs:attribute name="pattern" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                            <xs:element name="endDateTimeColumn">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                    <xs:attribute name="pattern" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                            <xs:element name="locationColumn">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                            <xs:element name="valueColumn">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                            <xs:element name="propertyColumn" maxOccurs="unbounded">
                                                <xs:complexType>
                                                    <xs:attribute name="name" type="xs:string"/>
                                                    <xs:attribute name="key" type="xs:string"/>
                                                </xs:complexType>
                                            </xs:element>
                                        </xs:sequence>
                                    </xs:complexType>
                                </xs:element>
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                    <xs:element name="timeSeriesSet" minOccurs="0" maxOccurs="1">
                        <xs:complexType>
                            <xs:sequence>
                                <xs:element name="moduleInstanceId" type="xs:string"/>
                                <xs:element name="valueType" type="xs:string"/>
                                <xs:element name="parameterId" type="xs:string"/>
                                <xs:element name="locationId" type="xs:string"/>
                                <xs:element name="timeStep" type="xs:string"/>
                                <xs:element name="readWriteMode" type="xs:string"/>
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:sequence>
            </xs:complexType>
        </xs:element>

    </xs:schema>"""

    schema_path = tmp_path / "test_schema.xsd"
    schema_path.write_text(schema_content)
    return str(schema_path)


@pytest.fixture
def fews_schema():
    """Fixture providing FEWS schema files."""
    # Create a clean schemas directory
    schemas_dir = TOOLS_DIR / "schemas"
    if schemas_dir.exists():
        shutil.rmtree(schemas_dir)
    schemas_dir.mkdir(parents=True, exist_ok=True)

    # Let xmlschema handle downloading and managing schemas
    schema_url = (
        "https://fewsdocs.deltares.nl/schemas/version1.0/timeSeriesImportRun.xsd"
    )
    download_schemas(schema_url, str(schemas_dir))

    # The schema will be in the schemas directory
    schema_path = schemas_dir / os.path.basename(schema_url)
    return str(schema_path)


@pytest.fixture
def valid_import_xml():
    """Fixture providing a valid XML document."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <fews:import xmlns:fews="http://www.wldelft.nl/fews"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <fews:general>
            <fews:importType>generalCSV</fews:importType>
            <fews:folder>import/annotations</fews:folder>
            <fews:table>
                <fews:dateTimeColumn name="CREATION_TIME" pattern="dd-MM-yyyy HH:mm"/>
                <fews:startDateTimeColumn name="START" pattern="dd-MM-yyyy HH:mm"/>
                <fews:endDateTimeColumn name="END" pattern="dd-MM-yyyy HH:mm"/>
                <fews:locationColumn name="LOC"/>
                <fews:valueColumn name="ANNOTATION"/>
                <fews:propertyColumn name="CATEGORIE" key="Categorie"/>
                <fews:propertyColumn name="SUB-CATEGORIE" key="Sub-Categorie"/>
            </fews:table>
        </fews:general>
        <fews:timeSeriesSet>
            <fews:moduleInstanceId>ImportAnnotationsModule</fews:moduleInstanceId>
            <fews:valueType>scalar</fews:valueType>
            <fews:parameterId>H.meting</fews:parameterId>
            <fews:locationId>LOC123</fews:locationId>
            <fews:timeStep>nonequidistant</fews:timeStep>
            <fews:readWriteMode>add originals</fews:readWriteMode>
        </fews:timeSeriesSet>
    </fews:import>
    """


@pytest.fixture
def valid_timeseries_import_run_xml():
    """Fixture providing a valid timeSeriesImportRun XML document."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <fews:timeSeriesImportRun xmlns:fews="http://www.wldelft.nl/fews">
        <fews:import>
            <fews:general>
                <fews:importType>generalCSV</fews:importType>
                <fews:folder>import/annotations</fews:folder>
                <fews:table>
                    <fews:dateTimeColumn name="CREATION_TIME" pattern="dd-MM-yyyy HH:mm"/>
                    <fews:startDateTimeColumn name="START" pattern="dd-MM-yyyy HH:mm"/>
                    <fews:endDateTimeColumn name="END" pattern="dd-MM-yyyy HH:mm"/>
                    <fews:locationColumn name="LOC"/>
                    <fews:valueColumn name="ANNOTATION"/>
                    <fews:propertyColumn name="CATEGORIE" key="Categorie"/>
                    <fews:propertyColumn name="SUB-CATEGORIE" key="Sub-Categorie"/>
                </fews:table>
                <fews:validate>true</fews:validate>
                <fews:importTimeZone>
                    <fews:timeZoneOffset>+01:00</fews:timeZoneOffset>
                </fews:importTimeZone>
            </fews:general>
            <fews:timeSeriesSet>
                <fews:moduleInstanceId>ImportAnnotationsModule</fews:moduleInstanceId>
                <fews:valueType>scalar</fews:valueType>
                <fews:parameterId>H.meting</fews:parameterId>
                <fews:locationId>LOC123</fews:locationId>
                <fews:timeSeriesType>external historical</fews:timeSeriesType>
                <fews:timeStep unit="nonequidistant"/>
                <fews:readWriteMode>add originals</fews:readWriteMode>
            </fews:timeSeriesSet>
        </fews:import>
    </fews:timeSeriesImportRun>
    """


@pytest.fixture
def invalid_import_xml():
    """Fixture providing an invalid XML document (missing required elements)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <fews:import xmlns:fews="http://www.wldelft.nl/fews"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <fews:general>
            <!-- Missing required importType -->
            <fews:folder>import/annotations</fews:folder>
            <fews:table>
                <fews:dateTimeColumn name="CREATION_TIME" pattern="dd-MM-yyyy HH:mm"/>
                <!-- Missing other required columns -->
            </fews:table>
        </fews:general>
    </fews:import>
    """


@pytest.mark.asyncio
async def test_validate_full_xml(valid_import_xml, mock_context, schema_file):
    """Test validation of a complete valid XML document."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=valid_import_xml, schema_url=schema_file, cache_schema=False
        ),
    )

    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_invalid_xml(invalid_import_xml, mock_context, schema_file):
    """Test validation of an invalid XML document."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=invalid_import_xml, schema_url=schema_file, cache_schema=False
        ),
    )

    assert not result.is_valid
    assert result.errors
    # Check for missing required element error
    assert any(
        "Tag 'fews:startDateTimeColumn' expected" in error for error in result.errors
    )


@pytest.mark.asyncio
async def test_validate_partial_xml(valid_import_xml, mock_context, schema_file):
    """Test partial validation using XPath."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=valid_import_xml,
            schema_url=schema_file,
            xpath=".//fews:general",
            cache_schema=False,
        ),
    )

    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_nonexistent_xpath(valid_import_xml, mock_context, schema_file):
    """Test validation with non-existent XPath."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=valid_import_xml,
            schema_url=schema_file,
            xpath=".//nonexistent",
            cache_schema=False,
        ),
    )

    assert not result.is_valid
    assert "XPath './/nonexistent' not found in XML" in result.errors[0]


@pytest.mark.asyncio
async def test_validate_missing_schema(valid_import_xml, mock_context):
    """Test validation with a non-existent schema file."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=valid_import_xml,
            schema_url="nonexistent.xsd",
            cache_schema=False,
        ),
    )

    assert not result.is_valid
    assert any("Failed to load schema" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_invalid_xml_content(mock_context, schema_file):
    """Test validation with invalid XML content."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content="<invalid>xml",  # Malformed XML
            schema_url=schema_file,
            cache_schema=False,
        ),
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.asyncio
async def test_validate_no_input():
    """Test validation with missing required input parameters."""
    with pytest.raises(ValidationError):
        XMLValidationInput()


@pytest.mark.asyncio
async def test_validate_partial_missing_namespace(mock_context, schema_file):
    """Test partial validation with XML missing required namespace."""
    xml_without_ns = """<?xml version="1.0" encoding="UTF-8"?>
    <import>
        <general>
            <importType>generalCSV</importType>
        </general>
    </import>
    """

    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=xml_without_ns,
            schema_url=schema_file,
            xpath=".//general",
            cache_schema=False,
        ),
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.asyncio
async def test_validate_with_nested_schema(
    valid_timeseries_import_run_xml, mock_context, fews_schema
):
    """Test validation using a schema with nested includes."""
    result = await validate_xml(
        mock_context,
        XMLValidationInput(
            xml_content=valid_timeseries_import_run_xml,
            schema_url=fews_schema,
            cache_schema=True,
        ),
    )

    assert result.is_valid
    assert not result.errors
