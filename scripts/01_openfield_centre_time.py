"""
Open Field Arena – Centre-Zone Dwell-Time Analysis
====================================================
Processes DeepLabCut (DLC) tracking files from a circular open-field arena
and quantifies time spent in a user-defined centre zone vs. the periphery.

Pipeline
--------
1. Load each DLC CSV (multi-index header).
2. Extract x / y coordinates for the 'Center' body-part.
3. Filter low-confidence frames (likelihood < threshold) → interpolate gaps.
4. Estimate arena geometry from percentile-based coordinate bounds.
5. Classify every frame as centre or periphery.
6. (Optional) Render a trajectory QC plot per animal.
7. Export per-animal processed CSVs + a group-level summary CSV.

Usage
-----
    python 01_openfield_centre_time.py

Edit the PARAMETERS block below to match your data.

Author : <your name>
Date   : 2025
License: MIT
"""

import os
import glob

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ──────────────────────────────────────────────────────────────
# PARAMETERS  ← edit here
# ──────────────────────────────────────────────────────────────
DATA_FOLDER       = "/Volumes/PortableSSD/DeepOF/atg7KD_SingleOF_males/Single_HFD"
OUTPUT_FOLDER     = "/Volumes/PortableSSD/DeepOF/atg7KD_SingleOF_males/Single_HFD/Processed_CentreTime"
FPS               = 15           # camera frame rate
BODYPART          = "center"     # DLC body-part label (case-insensitive)
CONF_THRESHOLD    = 0.9          # minimum DLC likelihood to keep a frame
CENTRE_FRACTION   = 0.6          # centre-zone radius = arena_radius × this value
ARENA_PERCENTILE  = (1, 99)      # percentile bounds for arena edge estimation
VISUAL_QC         = True         # set False to skip trajectory plots
# ──────────────────────────────────────────────────────────────


def load_dlc_bodypart(file_path: str, bodypart: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load x, y, likelihood arrays for a single body-part from a DLC CSV.

    Parameters
    ----------
    file_path : str
        Path to the DLC-generated CSV file (3-row multi-index header).
    bodypart : str
        Body-part label to extract (case-insensitive).

    Returns
    -------
    x, y, likelihood : np.ndarray
        Raw coordinate and confidence arrays (one value per frame).
    """
    df = pd.read_csv(file_path, header=[0, 1, 2])
    bp_cols = [col for col in df.columns if col[1].strip().lower() == bodypart.lower()]

    if len(bp_cols) < 3:
        raise ValueError(
            f"Expected ≥3 columns for body-part '{bodypart}' in {file_path}, "
            f"found {len(bp_cols)}."
        )

    x          = df[bp_cols[0]].values.astype(float)
    y          = df[bp_cols[1]].values.astype(float)
    likelihood = df[bp_cols[2]].values.astype(float)
    return x, y, likelihood


def clean_and_interpolate(
    x: np.ndarray,
    y: np.ndarray,
    likelihood: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Mask low-confidence frames as NaN, then linearly interpolate gaps.

    Parameters
    ----------
    x, y       : np.ndarray  Raw coordinate arrays.
    likelihood : np.ndarray  Per-frame DLC confidence scores.
    threshold  : float       Frames below this value are masked.

    Returns
    -------
    x_clean, y_clean : np.ndarray  Cleaned, interpolated coordinate arrays.
    """
    x = x.copy().astype(float)
    y = y.copy().astype(float)

    mask = likelihood < threshold
    x[mask] = np.nan
    y[mask] = np.nan

    x = pd.Series(x).interpolate(limit_direction="both").values
    y = pd.Series(y).interpolate(limit_direction="both").values
    return x, y


def estimate_arena(
    x: np.ndarray,
    y: np.ndarray,
    percentile: tuple[float, float] = (1, 99),
    centre_fraction: float = 0.6,
) -> tuple[float, float, float, float]:
    """
    Estimate circular arena geometry from coordinate percentiles.

    Parameters
    ----------
    x, y            : np.ndarray  Coordinate arrays (NaNs ignored).
    percentile      : tuple       Lower and upper percentile bounds.
    centre_fraction : float       Centre-zone radius as fraction of arena radius.

    Returns
    -------
    cx, cy, arena_radius, centre_radius : float
    """
    valid    = ~np.isnan(x) & ~np.isnan(y)
    xmin, xmax = np.percentile(x[valid], percentile[0]), np.percentile(x[valid], percentile[1])
    ymin, ymax = np.percentile(y[valid], percentile[0]), np.percentile(y[valid], percentile[1])

    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    arena_radius  = min(xmax - xmin, ymax - ymin) / 2
    centre_radius = arena_radius * centre_fraction
    return cx, cy, arena_radius, centre_radius


def plot_trajectory_qc(
    x: np.ndarray,
    y: np.ndarray,
    cx: float,
    cy: float,
    arena_radius: float,
    centre_radius: float,
    title: str = "",
) -> None:
    """Render a trajectory plot with arena and centre-zone overlays."""
    theta = np.linspace(0, 2 * np.pi, 360)
    fig, ax = plt.subplots(figsize=(6, 6))

    ax.plot(x, y, lw=0.5, alpha=0.3, color="steelblue", label="Trajectory")
    ax.plot(cx + arena_radius  * np.cos(theta),
            cy + arena_radius  * np.sin(theta), "g-", lw=1.5, label="Arena boundary")
    ax.plot(cx + centre_radius * np.cos(theta),
            cy + centre_radius * np.sin(theta), "r--", lw=1.5, label="Centre zone")
    ax.scatter([cx], [cy], c="red", s=40, zorder=5)

    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_xlabel("x (px)")
    ax.set_ylabel("y (px)")
    plt.tight_layout()
    plt.show()


def process_file(file_path: str, visual_qc: bool = True) -> dict:
    """
    Run the full pipeline for a single DLC CSV file.

    Parameters
    ----------
    file_path  : str   Path to DLC CSV.
    visual_qc  : bool  Whether to show the trajectory QC plot.

    Returns
    -------
    dict  Summary row for the group-level results table.
    """
    animal_id = os.path.splitext(os.path.basename(file_path))[0]
    print(f"\n── Processing: {animal_id}")

    # 1. Load
    x, y, likelihood = load_dlc_bodypart(file_path, BODYPART)

    # 2. Clean & interpolate
    x, y = clean_and_interpolate(x, y, likelihood, CONF_THRESHOLD)

    # 3. Estimate arena geometry
    cx, cy, arena_radius, centre_radius = estimate_arena(
        x, y,
        percentile=ARENA_PERCENTILE,
        centre_fraction=CENTRE_FRACTION,
    )
    print(f"   Arena centre: ({cx:.1f}, {cy:.1f}) | radius: {arena_radius:.1f} px | "
          f"centre zone: {centre_radius:.1f} px")

    # 4. Optional QC plot
    if visual_qc:
        plot_trajectory_qc(x, y, cx, cy, arena_radius, centre_radius, title=animal_id)

    # 5. Classify frames
    distances = np.linalg.norm(np.column_stack([x - cx, y - cy]), axis=1)
    in_centre = distances < centre_radius

    time_centre    = np.sum(in_centre)  / FPS
    time_periphery = np.sum(~in_centre) / FPS
    print(f"   Centre: {time_centre:.1f} s | Periphery: {time_periphery:.1f} s")

    # 6. Save per-animal CSV
    out_df = pd.DataFrame({
        "frame":                np.arange(len(x)),
        "x":                    x,
        "y":                    y,
        "distance_from_centre": distances,
        "in_centre":            in_centre,
    })
    out_path = os.path.join(OUTPUT_FOLDER, f"{animal_id}_processed.csv")
    out_df.to_csv(out_path, index=False)

    return {
        "animal":            animal_id,
        "n_frames":          len(x),
        "time_centre_sec":   time_centre,
        "time_periphery_sec": time_periphery,
        "centre_fraction":   round(time_centre / (time_centre + time_periphery), 4),
        "arena_radius_px":   round(arena_radius, 2),
        "centre_radius_px":  round(centre_radius, 2),
        "cx_px":             round(cx, 2),
        "cy_px":             round(cy, 2),
    }


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
def main() -> None:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(DATA_FOLDER, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {DATA_FOLDER}")

    print(f"Found {len(csv_files)} file(s) in {DATA_FOLDER}")

    summary = [process_file(fp, visual_qc=VISUAL_QC) for fp in csv_files]

    summary_df = pd.DataFrame(summary)
    summary_path = os.path.join(OUTPUT_FOLDER, "summary_open_field.csv")
    summary_df.to_csv(summary_path, index=False)

    print(f"\n✓ Done. Summary saved to: {summary_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
