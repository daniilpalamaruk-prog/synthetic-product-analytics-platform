# Samples

Generated Parquet is intentionally not committed. Create a compact deterministic sample with:

```bash
python generate.py --users 1000 --target-events 30000 --seed 42 --output sample/generated --inject-data-quality-issues false --csv-sample true
```

The output is ignored by Git. Use `python quality.py --input sample/generated --layer clean` to validate it.
