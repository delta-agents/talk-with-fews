"""
Standard FEWS flag and source mappings.

These mappings define all standard FEWS quality flags and their sources.
They are used to interpret flags and sources found in timeseries data.
"""

from .definitions import FlagDefinition, FlagSourceDefinition


QUALITY_FLAGS = {
    0: FlagDefinition(
        flag=0,
        origin="Original",
        quality="Reliable",
        description="Original value, passes all validation criteria",
    ),
    1: FlagDefinition(
        flag=1,
        origin="Corrected",
        quality="Reliable",
        description="Original value corrected through interpolation or manual editing",
    ),
    2: FlagDefinition(
        flag=2,
        origin="Completed",
        quality="Reliable",
        description="Original value was missing. Value has been filled in through interpolation, transformation (e.g. stage discharge) or a model",
    ),
    3: FlagDefinition(
        flag=3,
        origin="Original",
        quality="Doubtful",
        description="Observed value retrieved from external data source. Value is valid, but marked as suspect due to soft validation limits being exceeded",
    ),
    4: FlagDefinition(
        flag=4,
        origin="Corrected",
        quality="Doubtful",
        description="Original value was removed and corrected. However, the corrected value is doubtful due to validation limits",
    ),
    5: FlagDefinition(
        flag=5,
        origin="Completed",
        quality="Doubtful",
        description="Original value was missing. Value has been filled in as above, but resulting value is doubtful due to limits in transformation/interpolation or input value used for transformation being doubtful",
    ),
    6: FlagDefinition(
        flag=6,
        origin="Original",
        quality="Unreliable",
        description="Observed value retrieved from external data source. Value is invalid due to validation limits set. Value is marked as unreliable and will not be used in transformations and model calculations",
    ),
    7: FlagDefinition(
        flag=7,
        origin="Corrected",
        quality="Unreliable",
        description="Original value was removed and corrected. However, corrected value is unreliable",
    ),
    8: FlagDefinition(
        flag=8,
        origin="Completed",
        quality="Unreliable",
        description="Original value was missing. Value has been filled in as above, but resulting value is unreliable",
    ),
    9: FlagDefinition(
        flag=9,
        origin="Original",
        quality="Unreliable",
        description="Missing value in originally observed series. Note this is a special form of both Original/Unreliable and Original/Reliable",
    ),
}


FLAG_SOURCES = {
    # Primary Validation Sources
    "IMP": FlagSourceDefinition(
        code="IMP", description="Flag is imported", validation_type="primary"
    ),
    "SN": FlagSourceDefinition(
        code="SN", description="Soft minimum exceeded", validation_type="primary"
    ),
    "HN": FlagSourceDefinition(
        code="HN", description="Hard minimum exceeded", validation_type="primary"
    ),
    "SX": FlagSourceDefinition(
        code="SX", description="Soft maximum exceeded", validation_type="primary"
    ),
    "HX": FlagSourceDefinition(
        code="HX", description="Hard maximum exceeded", validation_type="primary"
    ),
    "ROR": FlagSourceDefinition(
        code="ROR", description="Rate of rise", validation_type="primary"
    ),
    "ROF": FlagSourceDefinition(
        code="ROF", description="Rate of fall", validation_type="primary"
    ),
    "SR": FlagSourceDefinition(
        code="SR", description="Same reading", validation_type="primary"
    ),
    "TS": FlagSourceDefinition(
        code="TS", description="Temporary shift", validation_type="primary"
    ),
    "OSC": FlagSourceDefinition(
        code="OSC", description="Oscillation", validation_type="primary"
    ),
    # Secondary Validation Sources
    "SC": FlagSourceDefinition(
        code="SC",
        description="Secondary validation, series comparison",
        validation_type="secondary",
    ),
    "FC": FlagSourceDefinition(
        code="FC",
        description="Secondary validation, flag comparison",
        validation_type="secondary",
    ),
    "MK": FlagSourceDefinition(
        code="MK",
        description="Secondary validation, Mann-Kendall test",
        validation_type="secondary",
    ),
    "SVP": FlagSourceDefinition(
        code="SVP",
        description="Secondary validation, Flag persistency",
        validation_type="secondary",
    ),
    "SFP": FlagSourceDefinition(
        code="SFP", description="Start flag persistency", validation_type="secondary"
    ),
    "MAN": FlagSourceDefinition(
        code="MAN", description="Manual edit", validation_type="secondary"
    ),
    "CA": FlagSourceDefinition(
        code="CA", description="Conditional aggregation", validation_type="secondary"
    ),
}
