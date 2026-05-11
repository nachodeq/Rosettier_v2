# Create Rosetta (metadata)

Rosettier supports creating Rosetta (metadata) tables for 96- and 384-well plates.

## In the app

1. Select plate size (96 or 384).
2. Add variable columns (for example: `condition`, `strain`, `dose`).
3. Select wells and assign values.
4. Repeat until all wells are annotated.
5. Export as CSV/TSV.

## Good practices

- Standardize categorical values early (e.g., avoid both `ctrl` and `control`).
- Include all experimental factors needed for downstream grouping.
- Validate that each expected well is present before analysis.
