# Camera CSV Import Format

Camera Monitor imports cameras from standard comma-separated values (CSV) files.

## File Requirements
- **Encoding**: UTF-8 or UTF-8 with BOM (`utf-8-sig`).
- **Delimiter**: Comma (`,`). Semicolon-separated files are rejected with a hint.
- **Line Endings**: CRLF (`\r\n`) or LF (`\n`). Blank lines are skipped.
- **Header Line** (must be row 1): `camera_name,location,description,ip_address`
- **Size Limits**: Minimum 1 data row, maximum 1000 data rows, file size up to 1 MiB.

## Column Constraints
1. **camera_name**: 1–100 characters. No control characters.
2. **location**: 1–100 characters. No control characters.
3. **description**: 1–500 characters. No control characters.
4. **ip_address**: Valid IPv4 host address. Must be unique in the file and database. Rejects `0.0.0.0`, multicast (`224.0.0.0/4`), broadcast (`255.255.255.255`), and leading zeroes.
