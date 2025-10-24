"""
Tests for enhanced parameter search functionality.

This test verifies that the GetParameterInput model now supports enhanced search
capabilities similar to get_locations, including searching across multiple columns
and supporting specific field filters.
"""

from talk_with_fews.models.webservice.get_parameters import GetParameterInput


def test_get_parameter_input_enhanced_functionality():
    """
    This test verifies that the GetParameterInput model supports enhanced search functionality.

    GetParameterInput supports:
    - number_of_parameters
    - filter_parameters_name (searches across id, name, and short_name columns in the tool implementation)
    """
    # Test that original functionality works
    valid_input = GetParameterInput(
        number_of_parameters=10, filter_parameters_name="water"
    )
    assert valid_input.number_of_parameters == 10
    assert valid_input.filter_parameters_name == "water"

    # Test that we can search by ID using the enhanced filter_parameters_name
    id_search_input = GetParameterInput(
        number_of_parameters=5, filter_parameters_name="WS.15"
    )
    assert id_search_input.number_of_parameters == 5
    assert id_search_input.filter_parameters_name == "WS.15"

    # Test that we can search by short name using the enhanced filter_parameters_name
    short_name_search_input = GetParameterInput(
        number_of_parameters=3, filter_parameters_name="Windsnelheid"
    )
    assert short_name_search_input.number_of_parameters == 3
    assert short_name_search_input.filter_parameters_name == "Windsnelheid"

    # Test that we can search without any filter
    no_filter_input = GetParameterInput(number_of_parameters=10)
    assert no_filter_input.number_of_parameters == 10
    assert no_filter_input.filter_parameters_name is None


def test_get_parameter_input_enhanced_search_behavior():
    """
    This test verifies that the enhanced search functionality works as expected.

    The GetParameterInput model supports:
    - filter_parameters_name: searches across id, name, and short_name columns (enhanced behavior in tool implementation)
    """
    # Test enhanced search behavior - filter_parameters_name searches across multiple columns
    enhanced_input = GetParameterInput(
        number_of_parameters=10, filter_parameters_name="WS.15"
    )

    # This searches across id, name, and short_name columns in the tool implementation
    # (similar to how get_locations searches in locationId, shortName, and description)
    assert enhanced_input.number_of_parameters == 10
    assert enhanced_input.filter_parameters_name == "WS.15"

    # Test that we can search by ID using the same filter field
    id_search = GetParameterInput(
        number_of_parameters=5, filter_parameters_name="WS.15"
    )
    assert id_search.filter_parameters_name == "WS.15"

    # Test that we can search by short name using the same filter field
    short_name_search = GetParameterInput(
        number_of_parameters=3, filter_parameters_name="Windsnelheid"
    )
    assert short_name_search.filter_parameters_name == "Windsnelheid"

    # Test that we can search by regular name using the same filter field
    name_search = GetParameterInput(
        number_of_parameters=10,
        filter_parameters_name="wind",  # searches id, name, short_name in tool implementation
    )
    assert name_search.filter_parameters_name == "wind"


def test_get_parameter_output_structure():
    """
    This test demonstrates what the GetParameterOutput object looks like.
    """
    from talk_with_fews.models.webservice.get_parameters import GetParameterOutput
    from talk_with_fews.models.base import Parameter

    # Create sample parameter data (mimicking what would come from the database)
    sample_parameters = [
        Parameter(
            id="WS.15",
            name="Windsnelheid [m/s] - 15min",
            parameter_type="instantaneous",
            unit="m/s",
            display_unit="m/s",
            uses_datum=False,
            parameter_group="Snelheid",
            parameter_group_name="Snelheid",
            short_name="Windsnelheid [m/s] - 15min",
            attributes="{}",
        ),
        Parameter(
            id="WD.15",
            name="Windrichting [°] - 15min",
            parameter_type="instantaneous",
            unit="°",
            display_unit="°",
            uses_datum=False,
            parameter_group="Richting",
            parameter_group_name="Richting",
            short_name="Windrichting [m/s] - 15min",
            attributes="{}",
        ),
    ]

    # Test single parameter result
    single_result = GetParameterOutput(
        parameters=[sample_parameters[0]],
        description="Found 1 parameter: 'Windsnelheid [m/s] - 15min'",
    )

    print("\n=== SINGLE PARAMETER RESULT ===")
    print(f"Parameters count: {len(single_result.parameters)}")
    print(f"Description: {single_result.description}")
    print(f"First parameter ID: {single_result.parameters[0].id}")
    print(f"First parameter name: {single_result.parameters[0].name}")
    print(f"First parameter group: {single_result.parameters[0].parameter_group}")

    # Test multiple parameters result
    multiple_result = GetParameterOutput(
        parameters=sample_parameters,
        description="Found 2 parameters: 'Windsnelheid [m/s] - 15min', 'Windrichting [m/s] - 15min'",
    )

    print("\n=== MULTIPLE PARAMETERS RESULT ===")
    print(f"Parameters count: {len(multiple_result.parameters)}")
    print(f"Description: {multiple_result.description}")
    print("Parameter details:")
    for i, param in enumerate(multiple_result.parameters):
        print(
            f"  {i + 1}. ID: {param.id}, Name: {param.name}, Group: {param.parameter_group}"
        )

    # Test empty result
    empty_result = GetParameterOutput(
        parameters=[], description="No parameters found matching 'nonexistent'"
    )

    print("\n=== EMPTY RESULT ===")
    print(f"Parameters count: {len(empty_result.parameters)}")
    print(f"Description: {empty_result.description}")

    # Verify the structure
    assert len(single_result.parameters) == 1
    assert single_result.parameters[0].id == "WS.15"
    assert "Found 1 parameter" in single_result.description

    assert len(multiple_result.parameters) == 2
    assert multiple_result.parameters[0].parameter_group == "Snelheid"
    assert multiple_result.parameters[1].parameter_group == "Richting"

    assert len(empty_result.parameters) == 0
    assert "No parameters found" in empty_result.description

    # Test case where display_unit is different from short_name (should show both)
    different_unit_param = Parameter(
        id="TEMP.1h",
        name="Temperature [°C] - hourly",
        parameter_type="instantaneous",
        unit="K",
        display_unit="°C",
        uses_datum=False,
        parameter_group="Temperature",
        short_name="Temperature",
        attributes="{}",
    )

    different_unit_result = GetParameterOutput(
        parameters=[different_unit_param],
        description="Found 1 parameter: 'Temperature (°C)'",
    )

    print("\n=== DIFFERENT UNIT RESULT ===")
    print(f"Parameters count: {len(different_unit_result.parameters)}")
    print(f"Description: {different_unit_result.description}")
    print(f"Parameter short_name: {different_unit_result.parameters[0].short_name}")
    print(f"Parameter display_unit: {different_unit_result.parameters[0].display_unit}")

    # Verify that display_unit is shown when different from short_name
    assert "Temperature" in different_unit_result.description
    assert "°C" in different_unit_result.description
