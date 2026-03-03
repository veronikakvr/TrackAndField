# TrackAndField

A lightweight, reproducible pipeline for quantifying locomotor and exploratory behaviour in rodent open-field tests using [DeepLabCut (DLC)](https://github.com/DeepLabCut/DeepLabCut) tracking output.

---

## Overview

| Script | Language | Purpose |
|--------|----------|---------|
| `scripts/01_openfield_centre_time.py` | Python | Extracts x/y coordinates from DLC CSVs, estimates arena geometry, and quantifies time spent in the centre vs. periphery of a circular open-field arena |
| `scripts/02_bw_behaviour_correlation.R` | R | Computes Spearman correlations (with FDR correction) between body weight and DeepOF behavioural scores, producing a publication-ready faceted figure |

---

## Repository Structure

```
deepof-openfield-analysis/
├── scripts/
│   ├── 01_openfield_centre_time.py       # Python – centre-zone dwell-time
│   └── 02_bw_behaviour_correlation.R     # R – BW × behaviour correlations
├── data/
│   └── example/                          # Place example DLC CSVs here
├── figures/                              # Output figures (gitignored by default)
├── environment.yml                       # Conda environment spec
├── requirements.txt                      # pip fallback
└── README.md
```

---

## Requirements

### Python (script 01)

| Package | Tested version |
|---------|---------------|
| Python  | ≥ 3.10 |
| NumPy   | ≥ 1.24 |
| pandas  | ≥ 2.0 |
| Matplotlib | ≥ 3.7 |

**Install with conda (recommended):**

```bash
conda env create -f environment.yml
conda activate deepof-of
```

**Or with pip:**

```bash
pip install -r requirements.txt
```

### R (script 02)

```r
install.packages(c("tidyverse", "readxl", "ggpubr"))
```

Tested on R ≥ 4.3.

---

## Usage

### Script 01 – Centre-zone dwell time

1. Open `scripts/01_openfield_centre_time.py`.
2. Edit the **PARAMETERS** block at the top:

```python
DATA_FOLDER      = "/path/to/your/dlc/csvs"
OUTPUT_FOLDER    = "/path/to/output"
FPS              = 15       # camera frame rate
BODYPART         = "center" # DLC body-part label (case-insensitive)
CONF_THRESHOLD   = 0.9      # minimum DLC likelihood
CENTRE_FRACTION  = 0.6      # centre zone = arena_radius × this value
VISUAL_QC        = True     # show trajectory plots for QC
```

3. Run:

```bash
python scripts/01_openfield_centre_time.py
```

**Outputs** (written to `OUTPUT_FOLDER`):
- `<animal_id>_processed.csv` — per-frame x, y, distance from centre, zone label
- `summary_open_field.csv` — one row per animal with dwell times and arena metadata

---

### Script 02 – Body weight × behaviour correlations

1. Open `scripts/02_bw_behaviour_correlation.R`.
2. Edit the **PARAMETERS** block:

```r
FILE_PATH       <- "/path/to/Correlation_DeepOF_BW.xlsx"
SHEET_NAME      <- "SocialOF_chow"
CONDITIONS      <- c("control", "Atg7KD")
BEHAVIOUR_VARS  <- c("Social_Index", "Exploratory_Score", ...)
OUTPUT_PDF      <- "Correlation_BW_vs_Behaviour.pdf"
```

3. Source the script in RStudio or run from the terminal:

```bash
Rscript scripts/02_bw_behaviour_correlation.R
```

**Output:**
- A PDF figure with one column per behavioural parameter, rows split by sex, and per-group Spearman ρ and p-values annotated inline.

---

## Methods

### Arena estimation (script 01)

The open-field boundary is estimated from the 1st–99th percentile range of tracked coordinates, avoiding sensitivity to outlier frames. The centre zone is defined as a circle with radius = `CENTRE_FRACTION × arena_radius` (default 60 %), consistent with common open-field conventions.

Low-confidence frames (DLC likelihood < threshold) are masked as `NaN` and linearly interpolated before analysis.

### Correlation analysis (script 02)

Spearman's ρ is used throughout to accommodate non-normally distributed behavioural scores. Multiple-comparison correction is applied within each Sex × Condition group using the Benjamini–Hochberg FDR method (`p.adjust(method = "fdr")`).

---

## Example output

**Trajectory QC plot** (script 01):  
Each animal's trajectory is plotted with the estimated arena boundary (green) and centre zone (red dashed) overlaid for rapid visual inspection.

**Correlation figure** (script 02):  
Faceted scatter plot (Sex × Behavioural parameter) with per-group linear fits and inline Spearman ρ / p annotations.


---

## License

MIT © \<your name\>
>>>>>>> 7ad8216 (Add documents from local folder)
