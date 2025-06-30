"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List
from pydantic import BaseModel, Field

from talk_with_fews.models.base import TimeSeriesLink


class TransformationDetails(BaseModel):
    """Model representing the details of a transformation.

    A transformation is a process that converts input time series into output time series
    according to specific rules defined in a module configuration.
    """

    id: int = Field(..., description="Unique identifier of the transformation")
    desc: str = Field(..., description="Description of what the transformation does")
    ord_nr: int = Field(
        ...,
        description="Order number indicating the sequence in the module configuration",
    )
    config_file: str = Field(
        ..., description="Relative path to the module configuration file"
    )
    mic_id: int = Field(
        ..., description="Unique identifier of the module configuration"
    )
    modins: str = Field(
        ..., description="Name of the module instance containing this transformation"
    )
    time_series_links: List[TimeSeriesLink] = Field(
        ..., description="List of time series connected to this transformation"
    )

class TransformationDetailsInput(BaseModel):
    """Model for the input of the get_transformation_details tool.

    This model defines the required parameters to get details about a specific transformation.

    Attributes:
        transformation_id: The unique identifier of the transformation to describe
    """

    transformation_id: int = Field(
        ..., description="The unique identifier of the transformation to describe"
    )
    
class TransformationDetailsOutput(BaseModel):
    """Model for the output of the get_transformation_details tool.

    This model provides a complete description of a transformation, including both its structured data
    and a formatted markdown representation for display purposes.
    """

    results: List[TransformationDetails] = Field(
        ...,
        description="List containing the transformation details and its associated time series links",
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the transformation information in a human-readable format",
    )

