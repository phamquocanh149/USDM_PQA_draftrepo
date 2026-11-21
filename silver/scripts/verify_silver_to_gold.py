#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Script: Silver-to-Gold Compatibility Adapter
=========================================================
Verifies that the Silver GeoParquet polygons can faithfully reproduce
the Gold Layer (usdmfinal.csv) with high fidelity.

Performs point-in-polygon spatial querying for Gold grid centroids against
Silver cleaned polygons and computes cell-by-cell concordance metrics.

Author: Senior Geospatial Data Engineer
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s")
logger = logging.getLogger("SilverToGoldVerifier")


def load_gold_sample(gold_path: Path, target_time_id: str) -> pd.DataFrame:
    """Loads a specific week from Gold usdmfinal.csv."""
    logger.info(f"Loading Gold records for time_id={target_time_id} from {gold_path}...")
    # Read chunked or filtered to optimize memory
    chunks = []
    for chunk in pd.read_csv(gold_path, chunksize=50000, dtype={"time": str, "grid": str, "drought": str}):
        matched = chunk[chunk["time"] == target_time_id]
        if not matched.empty:
            chunks.append(matched)
        elif chunks:  # If we already found the chunk and now past it
            break
    if not chunks:
        raise ValueError(f"Time {target_time_id} not found in Gold dataset.")
    df = pd.concat(chunks, ignore_index=True)
    logger.info(f"Loaded {len(df)} Gold records for week {target_time_id}.")
    return df


def verify_week(
    silver_week_parquet: Path, gold_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Simulates Gold recreation from Silver and evaluates concordance against Gold.
    """
    logger.info(f"Reading Silver partition from {silver_week_parquet}...")
    silver_gdf = gpd.read_parquet(silver_week_parquet)

    # Prepare Gold points as GeoDataFrame
    geometry = [Point(xy) for xy in zip(gold_df["lon"], gold_df["lat"])]
    gold_pts_gdf = gpd.GeoDataFrame(gold_df.copy(), geometry=geometry, crs="EPSG:4326")

    # Perform Spatial Join (point within polygon)
    # USDM polygons: mutually exclusive, higher DM takes precedence if overlap on boundaries
    # Sort silver by dm_value ascending so higher DM overwrites lower DM if any edge ambiguity
    silver_sorted = silver_gdf.sort_values(by="dm_value", ascending=True)

    joined = gpd.sjoin(
        gold_pts_gdf,
        silver_sorted[["dm_value", "drought_category", "geometry"]],
        how="left",
        predicate="within",
    )

    # In case a point lands on boundary between two polygons, take max dm_value
    joined_agg = joined.groupby(["time", "grid", "lon", "lat", "drought"], as_index=False).agg({
        "drought_category": "last"
    })

    # Default to '0' (No drought) if outside any DM polygon
    joined_agg["pred_drought"] = joined_agg["drought_category"].fillna("0")

    # Compare
    total_cells = len(joined_agg)
    exact_matches = (joined_agg["drought"] == joined_agg["pred_drought"]).sum()
    concordance = exact_matches / total_cells * 100.0

    mismatches = joined_agg[joined_agg["drought"] != joined_agg["pred_drought"]]

    result = {
        "time_id": gold_df["time"].iloc[0],
        "total_gold_cells": total_cells,
        "exact_matches": int(exact_matches),
        "mismatches_count": int(len(mismatches)),
        "concordance_percentage": round(concordance, 4),
        "mismatch_breakdown": mismatches.groupby(["drought", "pred_drought"]).size().to_dict(),
    }
    return result


def main():
    script_dir = Path(__file__).resolve().parent
    # repo_root is 2 levels up from silver/scripts/
    repo_root = script_dir.parent.parent if (script_dir.parent.parent / "silver").exists() else script_dir.parent
    default_silver = repo_root / "silver" / "data"
    default_gold = repo_root / "gold" / "data" / "usdmfinal.csv"

    parser = argparse.ArgumentParser(description="Verify Silver-to-Gold reproduction.")
    parser.add_argument(
        "--silver-root",
        type=Path,
        default=default_silver,
        help="Path to Silver root.",
    )
    parser.add_argument(
        "--gold-csv",
        type=Path,
        default=default_gold,
        help="Path to Gold usdmfinal.csv.",
    )
    parser.add_argument(
        "--weeks",
        nargs="+",
        default=["20200107", "20210601", "20220628"],
        help="List of time_ids to verify.",
    )
    args = parser.parse_args()

    for time_id in args.weeks:
        date_iso = f"{time_id[:4]}-{time_id[4:6]}-{time_id[6:]}"
        partition = (
            args.silver_root
            / "drought_polygons"
            / f"week_date={date_iso}"
            / "data.parquet"
        )
        if not partition.exists():
            logger.warning(f"Partition not found: {partition}. Run pipeline first.")
            continue

        gold_df = load_gold_sample(args.gold_csv, time_id)
        metrics = verify_week(partition, gold_df)
        print(f"\n--- Verification Result for Week {time_id} ---")
        for k, v in metrics.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()



