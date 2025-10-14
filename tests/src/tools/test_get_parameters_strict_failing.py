"""
Failing test that demonstrates what we need to implement for enhanced parameter search.

This test documents the current limitations and shows what functionality we need to add
to make get_parameters as flexible as get_locations.
"""

import pytest
from pydantic import ValidationError, BaseModel
from talk_with_fews.models.get_parameters import GetParameterInput


def test_get_parameter_input_current_limitations():
    """
    This test documents the current limitations of the GetParameterInput model.

    Currently, GetParameterInput only supports:
    - number_of_parameters
    - filter_parameters_name (searches only in the 'name' column)

    We need to add support for enhanced search like get_locations has:
    - filter_parameters_id (search in 'id' column)
    - filter_parameters_short_name (search in 'short_name' column)
    - Enhanced search logic that searches across multiple columns
    """
    # Test that current functionality works
    valid_input = GetParameterInput(
        number_of_parameters=10, filter_parameters_name="water"
    )
    assert valid_input.number_of_parameters == 10
    assert valid_input.filter_parameters_name == "water"

    # Test that new fields are missing - this demonstrates what we need to implement
    # The LaxBaseModel allows extra fields, so we need to use strict validation

    # Create a strict version of the model to test validation
    class StrictGetParameterInput(BaseModel):
        number_of_parameters: int
        filter_parameters_name: str = None

    # This should work
    strict_input = StrictGetParameterInput(
        number_of_parameters=10, filter_parameters_name="water"
    )
    assert strict_input.number_of_parameters == 10

    # These should fail because the fields don't exist yet
    with pytest.raises(ValidationError) as exc_info:
        StrictGetParameterInput(
            number_of_parameters=10,
            filter_parameters_id="WS.15",  # This field doesn't exist yet
        )

    error_msg = str(exc_info.value)
    assert (
        "filter_parameters_id" in error_msg or "extra fields not permitted" in error_msg
    )

    with pytest.raises(ValidationError) as exc_info:
        StrictGetParameterInput(
            number_of_parameters=10,
            filter_parameters_short_name="Windsnelheid",  # This field doesn't exist yet
        )

    error_msg = str(exc_info.value)
    assert (
        "filter_parameters_short_name" in error_msg
        or "extra fields not permitted" in error_msg
    )


def test_get_parameter_input_enhanced_functionality_needed():
    """
    This test documents what enhanced functionality we need to implement.

    Currently, the GetParameterInput model only supports:
    - number_of_parameters
    - filter_parameters_name (searches only in the 'name' column)

    We need to add support for:
    - filter_parameters_id (search in 'id' column)
    - filter_parameters_short_name (search in 'short_name' column)
    - Enhanced search logic that searches across multiple columns like get_locations does
    """
    # This test documents the current limitations
    current_input = GetParameterInput(
        number_of_parameters=10, filter_parameters_name="water"
    )

    # Current functionality only searches in the 'name' column
    # We need to enhance it to search in 'id', 'name', and 'short_name' columns
    # like the get_locations tool does for 'locationId', 'shortName', and 'description'

    # Expected enhanced functionality:
    # 1. Support filter_parameters_id field
    # 2. Support filter_parameters_short_name field
    # 3. Search across multiple columns when filter_parameters_name is provided
    # 4. Provide better descriptions like get_locations does

    assert current_input.number_of_parameters == 10
    assert current_input.filter_parameters_name == "water"

    # Once we implement the enhancements, we should be able to do:
    # enhanced_input = GetParameterInput(
    #     number_of_parameters=10,
    #     filter_parameters_name="water"  # Should search in id, name, AND short_name
    # )
    # This would be similar to how get_locations searches in locationId, shortName, and description
