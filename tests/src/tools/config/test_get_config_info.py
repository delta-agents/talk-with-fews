"""Tests for get_config_info tool."""

import pytest

from talk_with_fews.models.base import Deps
from talk_with_fews.models.config.get_config_info import (
    GetConfigInfoInput,
    GetConfigInfoOutput,
)
from talk_with_fews.routers.setup_connections import CtxWithDeps
from talk_with_fews.tools.config.get_config_info import get_config_info


@pytest.mark.asyncio
async def test_get_config_info_returns_correct_structure():
    """Test that get_config_info returns the correct output structure."""
    # Arrange
    mock_config_name = "Test Configuration"
    mock_deps = Deps(
        db_path="data/fews_config.db3",
    )
    mock_deps.config_name = mock_config_name
    mock_ctx = CtxWithDeps(deps=mock_deps)
    input_data = GetConfigInfoInput()

    # Act
    result = await get_config_info(mock_ctx, input_data)

    # Assert
    assert isinstance(result, GetConfigInfoOutput)
    assert result.config_name == mock_config_name
    assert isinstance(result.description, str)
    assert len(result.description) > 0


@pytest.mark.asyncio
async def test_get_config_info_description_contains_config_name():
    """Test that the description contains the config name."""
    # Arrange
    mock_config_name = "Hoogheemraadschap van Delfland"
    mock_deps = Deps(
        db_path="data/fews_config.db3",
    )
    mock_deps.config_name = mock_config_name
    mock_ctx = CtxWithDeps(deps=mock_deps)
    input_data = GetConfigInfoInput()

    # Act
    result = await get_config_info(mock_ctx, input_data)

    # Assert
    assert mock_config_name in result.description
    assert "FEWS" in result.description
    assert "configuration" in result.description.lower()


@pytest.mark.asyncio
async def test_get_config_info_description_mentions_fews():
    """Test that the description mentions FEWS and its purpose."""
    # Arrange
    mock_config_name = "Test Config"
    mock_deps = Deps(
        db_path="data/fews_config.db3",
    )
    mock_deps.config_name = mock_config_name
    mock_ctx = CtxWithDeps(deps=mock_deps)
    input_data = GetConfigInfoInput()

    # Act
    result = await get_config_info(mock_ctx, input_data)

    # Assert
    assert "FEWS" in result.description
    assert "Forecast Early Warning System" in result.description
    assert "hydrological" in result.description.lower()
    assert "workflow" in result.description.lower()


@pytest.mark.asyncio
async def test_get_config_info_with_different_config_names():
    """Test get_config_info with various config names."""
    # Test with different config names
    config_names = [
        "Config A",
        "Hoogheemraadschap van Delfland",
        "Test-Config-123",
        "配置",  # Unicode characters
    ]

    for config_name in config_names:
        # Arrange
        mock_deps = Deps(
            db_path="data/fews_config.db3",
        )
        mock_deps.config_name = config_name
        mock_ctx = CtxWithDeps(deps=mock_deps)
        input_data = GetConfigInfoInput()

        # Act
        result = await get_config_info(mock_ctx, input_data)

        # Assert
        assert result.config_name == config_name
        assert config_name in result.description
        assert isinstance(result.description, str)
