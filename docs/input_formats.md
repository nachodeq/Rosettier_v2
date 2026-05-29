# Input Formats

## Rosetta (metadata) table

Expected as CSV/TSV with at minimum:

- `well` (e.g., `A01`, `H12`, `P24`)
- plate coordinates (`row`, `column`) for metadata-aware workflows
- any number of additional metadata columns (e.g., strain, treatment, dose)

## Plate-reader time-series table

Rosettier expects a wide-format plate-reader export that can be parsed into tidy records:

- one identifier column for time or cycle,
- one column per well (e.g., `A01`, `A02`, ...),
- numeric measurement values.

Use tab-delimited `.txt` or `.tsv` exports when available.

## Point-measurement table

Use point-measurement inputs when each well has one endpoint or snapshot value for a signal. The app can import multiple point-measurement files in one run, so independent signals such as OD, GFP, or luminescence can be analyzed together.

### Long format

Long files must include a well column named `Well` (case-insensitive). Provide the measurement/value column name in the app, or leave it blank when there is exactly one non-metadata measurement column. Extra columns, such as `plate` or `batch`, are preserved as metadata.

```text
Well;OD;plate
A01;0.125;plate_1
A02;0.133;plate_1
B01;0.242;plate_1
```

### Plate matrix format

Matrix files should contain row labels (`A`-`H` for 96-well plates or `A`-`P` for 384-well plates) and numeric column headers.

```text
row	1	2	3
A	0.125	0.133	0.140
B	0.242	0.251	0.260
```

The point-measurement parser supports auto-detected CSV/TSV/TXT delimiters and explicit tab, comma, or semicolon choices. Decimal separators can be auto-detected or forced to comma/point notation.

## Notes

- Keep well IDs zero-padded (e.g., `A01`, not `A1`) for robust merging.
- Ensure column headers are unique and clean.
- For point-measurement long files, keep `Well` values compatible with the selected plate size and use one row per well per file.
