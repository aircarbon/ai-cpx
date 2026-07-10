"""
Shared data loading utilities for the ai-cpx project.
Contains functions for loading configuration data and populating database collections.
Can be used by both application services and initialization scripts.
"""

import json
from pathlib import Path

from .models import RiskDimensionSpec, RiskType


def load_config_file(filename: str, config_subdir: str = "database") -> dict:
    # Find project root by looking for config directory
    current_path = Path(__file__).parent
    while current_path.parent != current_path:
        config_path = current_path / "config" / config_subdir / filename
        if config_path.exists():
            with open(config_path, encoding="utf-8") as file:
                return json.load(file)
        current_path = current_path.parent

    raise FileNotFoundError(f"Config file not found: {filename} in {config_subdir}")


async def populate_risk_dimensions() -> int:
    config_data = load_config_file("risk_dimensions.json")
    dimensions = config_data.get("dimensions", [])

    created_count = 0
    for dimension_data in dimensions:
        # Check if dimension already exists
        existing = await RiskDimensionSpec.find_one(RiskDimensionSpec.key == dimension_data["key"])
        if existing:
            continue

        # Create new risk dimension
        risk_dimension = RiskDimensionSpec(**dimension_data)
        await risk_dimension.insert()
        created_count += 1

    return created_count


async def populate_risk_types() -> int:
    config_data = load_config_file("risk_types.json")
    risks = config_data.get("risks", [])

    created_count = 0
    for risk_data in risks:
        # Check if risk type already exists
        existing = await RiskType.find_one(RiskType.risk_type == risk_data["risk_type"])
        if existing:
            continue

        # Create new risk type
        risk_type = RiskType(**risk_data)
        await risk_type.insert()
        created_count += 1

    return created_count


async def initialize_configuration_data() -> dict[str, int]:
    risk_dims_count = await populate_risk_dimensions()
    risk_types_count = await populate_risk_types()

    return {"risk_dimensions": risk_dims_count, "risk_types": risk_types_count}
