# Part C — Final Results

## Dataset validation
25,600 rows; 200 corners; 128 vectors per corner. Batches cover corners 0–4, 5–29, and 30–199.
No duplicate corner/input pairs or missing SPICE/ML leakage values. Logic outputs matched A+B+Cin on every row.

## Metric
Per-run error (%) = 100 × |ML − SPICE| / max(|SPICE|, 1e−18 A). MAPE is the mean per-run error; mean accuracy = 100% − MAPE.

## Summary
| Metric | Value |
|---|---:|
| Runs | 25,600 |
| Corners | 200 |
| Mean accuracy | **99.1673%** |
| MAPE | **0.8327%** |
| Median error | 0.6971% |
| P95 error | 2.1099% |
| Maximum error | 4.3267% |
| Mean signed error | -0.0708% |
| MAE | 8.52454e-08 A |
| RMSE | 1.33978e-07 A |

**99% target met:** mean accuracy is 99.1673%.

## Breakdown
- Worst corner MAPE: corner 17, 3.5659%.
- Best corner MAPE: corner 45, 0.0969%.
- Highest average vector MAPE: A=6, B=0, Cin=1: 0.9214%.
- Full detail: `per_corner_metrics.csv`, `per_input_vector_metrics.csv`, and `worst_25_cases.csv`.

## Part B context
Team handoff reports Part B gate MAPE 0.9649% (original corners) and 0.8813% (fresh evaluation). Part C's 0.8327% is whole-CLA error versus full-circuit SPICE and is not a like-for-like comparison.

## Figures
`partc_parity_log.png` (log-log parity), `partc_error_distribution.png` (error histogram), `partc_corner_mape.png` (corner trend).

## Interpretation
P95 error is 2.11% and maximum is 4.33%, so mean accuracy does not mean every run is within 1%. Mean signed error -0.0708% shows slight aggregate underprediction. This is analysis of provided CSVs; ngspice/netlists were not rerun independently.