# Data Mapping Configuration

All file-to-database mappings live in `config/column_mappings.yaml`. This keeps the ingest logic declarative so we can add new shipment layouts or tariffs without touching Python code.

## Structure

```yaml
region_map:            # province -> region mapping
shipments:             # shipment workbooks
  "<workbook name>":
    defaults:
      columns:         # base column mapping (source -> normalized field)
    sheets:
      "<sheet name>":
        origin_dc: CGY # optional per-sheet overrides (e.g., origin DC)
        columns: { ... }
summary_files:         # optional summary tables (region-level stats)
tariffs:               # tariff workbook definitions
  "<workbook name>":
    carrier_name: ...
    origin_dc: ...
    tariff_type: CWT | SKID_SPOT
    sheet: Sheet1
    dest_city_column: ...
    dest_province_column: ...
    min_charge_column: ...
    spot_columns: [...]        # for skid tariffs
    breaks:                    # for CWT tariffs
      - column: "L5CWT"
        from: 0
        to: 500
      - ...
```

## Adding a Shipment Workbook

1. Copy the exact filename (as uploaded) into the `shipments` section.
2. Under `defaults.columns`, map each source column to one of the normalized field names (`shipment_ref`, `origin_city`, `pallets`, `weight`, `dim_weight`, `charge`, etc.).
3. If the workbook has multiple sheets, add a `sheets` entry per tab and set `origin_dc` or sheet-specific columns.
4. Save the file and restart the backend (the loader caches the config).

During normalization, the config columns are merged with any mappings the user selects in the UI, and the `origin_dc` is applied per sheet.

## Adding a Tariff Workbook

1. Add an entry under `tariffs` with the workbook name.
2. Set `carrier_name`, `origin_dc`, and `tariff_type`.
3. Provide `dest_city_column`, `dest_province_column`, and `min_charge_column`.
4. For skid tariffs, list every `spot_columns` value (e.g., `"1"`-`"22"`).
5. For CWT tariffs, define `breaks` as either:
   - A list of column names (the loader will infer weight ranges), or
   - A list of `{column, from, to}` objects for explicit ranges.
6. Save and restart the backend; `tariff_ingestion.py` now reads the config at runtime.

## Tips

- Keep column names case-sensitive to match the Excel headers.
- Use the `region_map` entry to control how provinces roll up to regions in dashboards/PPTs.
- Because the loader is cached, modify the YAML and restart `uvicorn` (or call `load_mapping_config.cache_clear()` in a shell) to pick up changes.

