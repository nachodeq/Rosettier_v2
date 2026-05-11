# Input Formats

## Rosetta (metadata) table

Expected as CSV/TSV with at minimum:

- `well` (e.g., `A01`, `H12`, `P24`)
- plate coordinates (`row`, `column`) for metadata-aware workflows
- any number of additional metadata columns (e.g., strain, treatment, dose)

## Plate-reader table

Rosettier expects a wide-format plate-reader export that can be parsed into tidy records:

- one identifier column for time or cycle,
- one column per well (e.g., `A01`, `A02`, ...),
- numeric measurement values.

Use tab-delimited `.txt` or `.tsv` exports when available.

## Notes

- Keep well IDs zero-padded (e.g., `A01`, not `A1`) for robust merging.
- Ensure column headers are unique and clean.
