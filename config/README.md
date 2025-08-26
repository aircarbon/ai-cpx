# Configuration Files

This directory contains configuration files for the AI CPX application.

## Structure

```
config/
├── README.md              # This file
└── database/              # Database seeding configuration
    ├── risk_dimensions.json    # Risk dimension specifications
    └── risk_types.json         # Risk type definitions
```

## Database Configuration

The `database/` folder contains JSON files used to pre-populate the database with default configuration data:

### risk_dimensions.json
Defines the risk assessment dimensions used for scoring evidence. Each dimension includes:
- **key**: Unique identifier for the dimension
- **label**: Human-readable name
- **description**: What the dimension measures
- **rationale**: Why this dimension is important
- **guidance**: How to assess this dimension
- **higher_is_riskier**: Whether higher values indicate higher risk
- **scale**: Ordered list of possible values (lowest to highest)
- **mapping**: Numeric scores for each scale value
- **weight**: Relative importance in final scoring

### risk_types.json
Defines the types of risks that can be identified and assessed in carbon projects:
- **risk_type**: Unique identifier for the risk type
- **description**: Detailed description of the risk
- **weight**: Relative importance in overall project risk assessment

## Usage

These files are loaded by the database initialization scripts to populate the `RiskDimensionSpec` and `RiskType` collections in MongoDB.
