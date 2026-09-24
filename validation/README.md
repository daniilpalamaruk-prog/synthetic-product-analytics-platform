# Validation

`run.py` is the stable CLI entry point for Parquet validation:

```bash
python validation/run.py --input data/small --layer raw
python validation/run.py --input data/small --layer clean
```

It emits `quality_report.json` for raw and `quality_report_clean.json` for clean with PASS/WARN/FAIL results. SQL equivalents for warehouse monitoring live in `sql/quality/monitoring.sql`. Controlled anomalies are evaluated in raw; analytical work uses clean.
