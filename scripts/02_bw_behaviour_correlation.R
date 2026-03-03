# ============================================================
#  Spearman Correlation: Body Weight vs. Open-Field Behaviour
# ============================================================
#
#  Computes Spearman correlations (with FDR correction) between
#  body weight (BW) and a set of behavioural parameters, then
#  produces a faceted scatter plot with per-group regression
#  lines and inline annotation of ρ and p values.
#
#  Input  : Excel workbook with one sheet per cohort/diet.
#  Output : PDF figure saved to the working directory.
#
#  Usage  : Edit the PARAMETERS section, then source this script
#           or run it interactively chunk-by-chunk in RStudio.
#
#  Author : <your name>
#  Date   : 2025
#  License: MIT
# ============================================================


# ── Dependencies ─────────────────────────────────────────────
suppressPackageStartupMessages({
  library(tidyverse)
  library(readxl)
  library(ggpubr)
})


# ── PARAMETERS  ← edit here ──────────────────────────────────

FILE_PATH  <- "/Users/veronika/Nextcloud/Thesis/And so it begins/DATA_figures/OF/Correlation_DeepOF_BW.xlsx"
SHEET_NAME <- "SocialOF_chow"

# Experimental conditions to include (subset of what exists in the sheet)
CONDITIONS <- c("control", "Atg7KD")   # e.g. c("Atg7KD", "Atg7OE")

# Behavioural variables to correlate with BW
BEHAVIOUR_VARS <- c(
  "Social_Index",
  "Exploratory_Score",
  "Stastic_active",   # note: original spelling preserved
  "Static_passive",
  "Moving"
)

# Output figure filename (saved in the working directory)
OUTPUT_PDF <- "Correlation_BW_vs_Behaviour.pdf"
FIG_WIDTH  <- 16   # inches
FIG_HEIGHT <- 10   # inches

# ─────────────────────────────────────────────────────────────


# ── Colour palette (extend as needed) ────────────────────────
COLOUR_MAP <- c(
  "Female_control" = "#9D9D9D",
  "Female_Atg7KD"  = "#A44316",
  "Female_Atg7OE"  = "#411F54",
  "Male_control"   = "#000000",
  "Male_Atg7KD"    = "#444B29",
  "Male_Atg7OE"    = "#375685"
)


# ── 1. Load & filter data ─────────────────────────────────────
df_raw <- read_excel(FILE_PATH, sheet = SHEET_NAME)

df <- df_raw |>
  filter(Condition %in% CONDITIONS) |>
  mutate(
    Condition = factor(Condition, levels = CONDITIONS),
    Sex       = factor(Sex, levels = c("Female", "Male")),
    Diet      = factor(Diet)
  )

cat(sprintf(
  "Loaded %d rows | conditions: %s | diets: %s\n",
  nrow(df),
  paste(levels(df$Condition), collapse = ", "),
  paste(levels(df$Diet),      collapse = ", ")
))


# ── 2. Reshape to long format ─────────────────────────────────
long_df <- df |>
  pivot_longer(
    cols      = all_of(BEHAVIOUR_VARS),
    names_to  = "Parameter",
    values_to = "Value"
  ) |>
  mutate(
    SexCondition = paste(Sex, Condition, sep = "_"),
    Parameter    = factor(Parameter, levels = BEHAVIOUR_VARS)
  )


# ── 3. Spearman correlations with FDR correction ──────────────
cor_results <- long_df |>
  group_by(Sex, Condition, Parameter) |>
  summarise(
    n       = n(),
    rho     = cor(BW, Value, method = "spearman", use = "complete.obs"),
    p.value = cor.test(BW, Value, method = "spearman", exact = FALSE)$p.value,
    .groups = "drop"
  ) |>
  group_by(Sex, Condition) |>
  mutate(p.adjusted = p.adjust(p.value, method = "fdr")) |>
  ungroup()

print(cor_results, n = Inf)


# ── 4. Build inline annotation labels ────────────────────────
label_df <- cor_results |>
  mutate(
    SexCondition = paste(Sex, Condition, sep = "_"),

    # Formatted p-value for plotmath
    p_str  = if_else(p.value < 0.001, "< .001",
                     paste0("== ", formatC(p.value, digits = 3, format = "f"))),
    label  = paste0("italic(rho) == ", round(rho, 2), " ~ italic(p) ", p_str),

    # Annotation position: Females top-left, Males bottom-right
    x_side = if_else(Sex == "Female", -Inf, Inf),
    y_side = if_else(Sex == "Female",  Inf, -Inf),
    hjust  = if_else(Sex == "Female", -0.08, 1.08),

    # Vertical stacking offset per group
    v_stack = case_when(
      Sex == "Female" & Condition == CONDITIONS[1] ~  2.0,
      Sex == "Female" & Condition == CONDITIONS[2] ~  3.4,
      Sex == "Male"   & Condition == CONDITIONS[1] ~ -2.2,
      Sex == "Male"   & Condition == CONDITIONS[2] ~ -0.8,
      TRUE ~ 0
    )
  )


# ── 5. Active colour subset ───────────────────────────────────
active_groups  <- unique(long_df$SexCondition)
active_colours <- COLOUR_MAP[names(COLOUR_MAP) %in% active_groups]


# ── 6. Plot ───────────────────────────────────────────────────
p <- ggplot(long_df, aes(x = BW, y = Value, colour = SexCondition)) +

  # Points + regression lines
  geom_point(size = 2.5, alpha = 0.75) +
  geom_smooth(method = "lm", se = FALSE, linewidth = 0.8) +

  # Inline ρ / p annotations (parsed plotmath)
  geom_text(
    data        = label_df,
    aes(x       = x_side,
        y       = y_side,
        label   = label,
        colour  = SexCondition,
        vjust   = v_stack,
        hjust   = hjust),
    parse       = TRUE,
    size        = 4.2,
    fontface    = "bold",
    show.legend = FALSE,
    inherit.aes = FALSE
  ) +

  # Layout
  facet_grid(Sex ~ Parameter, scales = "free_y") +
  scale_y_continuous(expand = expansion(mult = c(0.25, 0.30))) +
  scale_colour_manual(values = active_colours) +

  # Theme
  theme_bw(base_size = 18) +
  theme(
    strip.text      = element_text(size = 17, face = "bold"),
    legend.position = "bottom",
    panel.spacing.y = unit(0.6, "lines")
  ) +

  labs(
    x      = "Body Weight (g)",
    y      = "Behavioural Score",
    colour = "Group",
    title  = sprintf(
      "Spearman Correlation: BW vs. Behaviour  |  %s  |  Diet: %s",
      paste(CONDITIONS, collapse = ", "),
      paste(unique(as.character(df$Diet)), collapse = ", ")
    )
  )

print(p)


# ── 7. Save figure ────────────────────────────────────────────
ggsave(
  filename = OUTPUT_PDF,
  plot     = p,
  width    = FIG_WIDTH,
  height   = FIG_HEIGHT,
  units    = "in",
  device   = cairo_pdf    # vector text rendering
)

cat(sprintf("\n✓ Figure saved: %s\n", OUTPUT_PDF))
