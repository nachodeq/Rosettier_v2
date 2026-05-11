# Publication notes (BMC Bioinformatics-oriented)

## Intended software-paper positioning

Rosettier v2 should be positioned as local, reproducible software for plate-reader growth curve analysis with explicit support for Rosetta (metadata) generation, metadata-aware integration, and exploratory feature extraction.

## Likely manuscript figures

1. End-to-end workflow schematic (Rosetta (metadata) creation -> import -> analysis -> export).
2. Example 96-well Rosetta (metadata) map and corresponding time-series summary.
3. Example 384-well analysis output and per-condition feature comparison.
4. Reproducibility figure showing identical outputs across Linux/macOS/Windows environments.

## Reproducibility checklist

- Versioned source tag and changelog entry.
- Frozen environment file (`environment.yml`).
- Included example datasets (96 and 384 well).
- Command-level install and launch instructions.
- Documented export artifacts and expected schema.

## Suggested benchmark/reviewer expectations

- Demonstrate successful execution on at least one Linux, one macOS, and one Windows (Miniforge) machine.
- Provide runtime profile for representative 96/384 datasets.
- Show feature stability/reproducibility from repeated runs.
- Compare pipeline outputs against a known reference or manually validated subset.

## Datasets/examples to include before submission

- Finalized curated 96-well example with clear condition metadata.
- Finalized curated 384-well example with clear condition metadata.
- Optional additional benchmark dataset for stress-testing parser robustness.
- Accompanying expected-output tables for reproducibility verification.
