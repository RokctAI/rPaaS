"""Merge series/parts/<class>_<cohort>.<runid>.parquet into series/<class>_<cohort>.parquet,
dropping duplicate series (keep first occurrence) in case of overlapping resumed runs."""
import glob
import os

import pyarrow.parquet as pq
import pyarrow as pa

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES_DIR = os.path.join(HERE, "series")
PARTS_DIR = os.path.join(SERIES_DIR, "parts")

groups = {}
for p in sorted(glob.glob(os.path.join(PARTS_DIR, "*.parquet"))):
    key = os.path.basename(p).rsplit(".", 2)[0]  # <class>_<cohort>
    groups.setdefault(key, []).append(p)

for key, paths in groups.items():
    out = os.path.join(SERIES_DIR, f"{key}.parquet")
    seen = set()
    writer = None
    n_rows = 0
    for p in paths:
        pf = pq.ParquetFile(p)
        for rg in range(pf.num_row_groups):
            tbl = pf.read_row_group(rg)
            sids = set(tbl.column("series_id").to_pylist())
            dupes = sids & seen
            if dupes:
                import pyarrow.compute as pc
                mask = pc.invert(pc.is_in(tbl.column("series_id"),
                                          value_set=pa.array(list(dupes))))
                tbl = tbl.filter(mask)
            seen |= sids
            if tbl.num_rows == 0:
                continue
            if writer is None:
                writer = pq.ParquetWriter(out, tbl.schema, compression="zstd")
            writer.write_table(tbl)
            n_rows += tbl.num_rows
    if writer:
        writer.close()
    print(f"{key}: {len(paths)} parts -> {out}  ({len(seen)} series, {n_rows} rows)")
print("finalize complete")
