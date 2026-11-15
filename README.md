# Team Triode — Semiconductor Device Leakage ML Project

This README consolidates the Parts A/B review, the Part C implementation handoff, and the completed Part C results. It records the methodology, validation, results, reproduction guidance, and limitations.

## Parts A and B — Review package

## Setup and Part A data generation

Team Triode: supplied 45nm_MGK model, nominal VDD 1 V, assigned 3-bit CLA for Part C. All MOS channel lengths are 45 nm. SPICE references were generated with ngspice 45.2.

For each of NMOS ON/OFF and PMOS ON/OFF, 10,000 independent random transistor examples were first drawn. VDD was uniform on 0.9–1.1 V; temperature on −40–125 °C; W on 45–360 nm; and Vd and Vs independently on 0–VDD. The five model parameters vth0, toxe, ndep, u0 and xj were each drawn independently within ±10% of their separate NMOS or PMOS nominal values. Vg/Vb followed the four fixed case biases in the project PDF. Each transistor netlist placed its drain, gate, source and body on separate voltage sources and set the required ngspice options. Four signed terminal currents were recorded per row.

The original 10,000 rows per case use fixed 70/15/15 training, validation and test splits (7,000/1,500/1,500). A second independently uniform 10,000-row set per case was added for refinement; combined training/validation/test counts are 14,000/3,000/3,000. Split indices are saved. Original test results appear in the main table; supplementary test metrics are in the refinement folders.

KCL was checked by summing Id+Ig+Is+Ib. The largest absolute residual across the original datasets was 9.49e−15 A; the largest relative residual was 4.67e−5, at very small total current. The three required temperature, threshold and oxide-thickness trends are shown in checks/physical_trends.png.


The four baseline algorithm families use the original 7,000 training rows per case. Final refinements use 14,000 distinct training rows with separate validation. The main transistor test table reports only the original 1,500 held-out rows; additional test metrics are saved in refinement folders. Small median-error advantages can coexist with worse R2 or tail errors. AND/OR internal inverter gate voltages are approximated by their logic rails because the four prescribed models fix Vg/Vb. These limitations must remain disclosed.

Assignment: 45 nm MGK, nominal 1 V. Part C (3-bit CLA) is outside this package.

## Measured Part B result

Across 3600 gate evaluations: median percentage error 0.7935%; mean percentage error 0.9649%; 95th-percentile error 2.3983%.
Nonpositive predictions: 0.

## Transistor held-out test results

| Case | Selected method | Median error % | 95th percentile % | R2 |
|---|---|---:|---:|---:|
| nmos_on | wider_independent_conserving_MLP | 0.4620 | 2.5727 | 0.999677 |
| nmos_off | zero_bias_normalized_MLP | 0.4370 | 6.3731 | 0.982659 |
| pmos_on | wider_independent_conserving_MLP | 0.3908 | 2.0608 | 0.999938 |
| pmos_off | zero_bias_normalized_MLP | 0.3514 | 5.1412 | 0.987355 |

## Gate/input results

| Gate | Input | Median error % | Mean error % | 95th percentile % |
|---|---|---:|---:|---:|
| INV | 0 | 1.0577 | 1.2539 | 3.1548 |
| INV | 1 | 0.6585 | 0.8296 | 2.1557 |
| NAND2 | 00 | 1.7382 | 1.6451 | 2.5419 |
| NAND2 | 01 | 0.7377 | 0.9851 | 2.8919 |
| NAND2 | 10 | 1.2293 | 1.2301 | 2.3527 |
| NAND2 | 11 | 0.6558 | 0.8286 | 2.1469 |
| NOR2 | 00 | 1.0481 | 1.2477 | 3.1544 |
| NOR2 | 01 | 0.7897 | 0.8534 | 1.8242 |
| NOR2 | 10 | 0.5226 | 0.7956 | 2.2797 |
| NOR2 | 11 | 0.7349 | 0.9539 | 2.6207 |
| AND2 | 00 | 0.8235 | 0.8858 | 1.8255 |
| AND2 | 01 | 0.6033 | 0.7782 | 2.0478 |
| AND2 | 10 | 0.6401 | 0.7058 | 1.6787 |
| AND2 | 11 | 0.6003 | 0.7690 | 2.0655 |
| OR2 | 00 | 0.8445 | 1.0689 | 3.3445 |
| OR2 | 01 | 0.7525 | 0.8362 | 1.8451 |
| OR2 | 10 | 0.6372 | 0.7867 | 2.0598 |
| OR2 | 11 | 0.6827 | 0.9154 | 3.1611 |

## Fresh, independent gate corners

Frozen selected models were evaluated on 3600 additional gate cases using seed 20261211: mean error 0.8813%, median 0.6916%, 95th percentile 2.1781%, nonpositive predictions 0.
These reference currents were never used for transistor fitting or selection. The earlier 200-corner gate set guided development decisions, so the fresh set is the stronger generalization check.

## Error analysis

Best gate/input by mean percentage error: AND2 10 (0.7058%). Worst: NAND2 00 (1.6451%).

The gate operating voltages often lie at or extremely close to the supply rails, whereas uniform transistor samples predominantly lie in the interior. This makes boundary generalization a limitation even when random held-out transistor errors are small. Predicted ON drain/source currents can be much larger than the net leakage, making direct subtraction ill-conditioned. The verified KCL aggregation avoids that subtraction. No fitted correction based on gate reference leakage is applied.

## Baseline model settings

- Polynomial ridge: standardized inputs, degree 3, alpha 0.01.
- Extra Trees: 150 trees, minimum leaf size 1, fixed random seed.
- Histogram gradient boosting: independent regressors per target, 150 iterations, 31 leaves, L2=0.1.
- Initial neural network: standardized inputs, 96x96 tanh layers, up to 500 iterations, early stopping. Refined neural variants and validation scores are recorded in selection_comparison.csv; four_method_comparison.csv reports the four algorithm families.
- Baseline signed log-magnitude models normalize current by width and learn signs separately. All predictions and reference values are retained without clipping negative gate leakage.

## Verification and interpretation

- The supplied model was verified byte-for-byte against model/45nm_MGK.pm in the downloaded archive. Its SHA256 is 4cda7bf16d5ca8eccaa0b8656ff8708f881f7f3c26cb706b7e9dcd465d5d0280.
- Four independent 10,000-row random transistor datasets; 70/15/15 splits with saved row indices. Gate results were not used for fitting or validation-based model selection.
- Four required baseline algorithm types were compared. Additional neural refinements were chosen using transistor validation error only. Held-out test metrics are reported, not used for model selection.
- Percentage error is 100*abs(pred-reference)/max(abs(reference),1e-18 A). Both current signs and raw predictions are retained; no negative predictions are silently clipped. R2 is a separate metric.
- Primary gate leakage is total positive-rail static current, including high input-source currents. VDD-only reference and prediction are also saved.
- Gate current is assembled at a KCL cut around the conducting high-rail component. This avoids subtracting poorly predicted large ON currents at tiny drain-source differences. The derivation was independently checked using SPICE current probes for each gate/input example.
- Internal and output voltages are supplied by SPICE, as allowed by Part B. These are reused, not independently predicted by ML.
- Gate sizing: NMOS 90 nm, PMOS 180 nm, all lengths 45 nm. All NMOS share one process draw per corner and all PMOS another.
- AND2 and OR2 references are complete cascaded transistor netlists. Intermediate inverter gate voltages are represented by their logic-state transistor model.
- The supplied oxide-parameter combination is retained. Ngspice may ignore dtox when inconsistent with explicit toxe and toxp. Only the five assigned process parameters were varied.
- High R2 does not establish 1% error. If the measured error exceeds target, this package is an implementation and evidence package, not a claim of target achievement.
- See checks/audit.json, checks/boundary_identity.json and gates/reference_checks.json for independent checks.

## Files and reproduction

Run commands from this folder with Ubuntu Python and ngspice 45.2. Required Python libraries are NumPy, SciPy, scikit-learn 1.7.2, joblib and matplotlib. Saved model loading should use matching versions.

1. python3 generate_data.py --samples 10000 --workers 8
2. python3 check_data.py
3. python3 train_models.py
4. python3 refine_neural.py
5. python3 continue_neural.py
6. python3 refine_uniform.py
7. python3 refine_conserving.py
8. python3 continue_conserving.py
9. python3 refine_residual.py
10. python3 refine_independent.py
11. python3 refine_wider.py
12. python3 refine_normalized.py
13. python3 gates.py
14. python3 verify_boundary.py
15. python3 finalize_part_ab.py
16. python3 evaluate_fresh_corners.py
17. python3 package_results.py

The saved archive contains results and model files, so these long-running training commands are for intentional regeneration. On an extracted archive, move previous output folders before regenerating data: stages use completed-case checkpoints. Keep the provided saved split indices and gate seeds with their corresponding datasets.

## Final model choices

Four different baseline methods were evaluated for every transistor case on the original validation split. Their unmodified 16-row results are in final_results/four_method_comparison.csv. The selected refinements below were compared separately in final_results/selection_comparison.csv, using the combined original and additional transistor validation rows; gate reference currents were never used in that selection.
- nmos_on: wider_independent_conserving_MLP, selected for its lower transistor validation median percentage error (0.4692%).
- nmos_off: zero_bias_normalized_MLP, selected for its lower transistor validation median percentage error (0.4206%).
- pmos_on: wider_independent_conserving_MLP, selected for its lower transistor validation median percentage error (0.3983%).
- pmos_off: zero_bias_normalized_MLP, selected for its lower transistor validation median percentage error (0.3437%).

The final neural variants predict signed terminal currents through a current-conserving decomposition: positive conductance, gate-current magnitude, and body-current magnitude. The selected wider independent models train separate 96x96 tanh networks for these quantities. The selected zero-bias models normalize OFF-state gate and body current by their voltage-distance factors before fitting separate 64x64 tanh networks. The currents are reconstructed so Id+Ig+Is+Ib=0. All neural inputs and log targets are standardized; fitting uses L-BFGS with fixed seeds, validation-selected checkpoints, and no gate reference labels.

## Complete gate results table

Currents and bias are in amperes; bias is mean(ML minus SPICE).

| Gate | Input | SPICE median A | ML median A | Bias A | Median error % | 95th percentile % |
|---|---|---:|---:|---:|---:|---:|
| INV | 0 | 1.051516e-07 | 1.050659e-07 | 1.564364e-10 | 1.0577 | 3.1548 |
| INV | 1 | 1.151717e-07 | 1.145363e-07 | -6.482753e-11 | 0.6585 | 2.1557 |
| NAND2 | 00 | 1.100132e-07 | 1.125279e-07 | 2.142520e-09 | 1.7382 | 2.5419 |
| NAND2 | 01 | 1.320879e-07 | 1.320535e-07 | -2.429265e-10 | 0.7377 | 2.8919 |
| NAND2 | 10 | 8.788973e-08 | 8.806260e-08 | 6.920741e-10 | 1.2293 | 2.3527 |
| NAND2 | 11 | 2.300385e-07 | 2.287683e-07 | -9.529444e-11 | 0.6558 | 2.1469 |
| NOR2 | 00 | 2.099323e-07 | 2.097233e-07 | 2.993379e-10 | 1.0481 | 3.1544 |
| NOR2 | 01 | 1.782398e-07 | 1.795998e-07 | 1.019072e-09 | 0.7897 | 1.8242 |
| NOR2 | 10 | 9.498909e-08 | 9.544352e-08 | 4.276754e-10 | 0.5226 | 2.2797 |
| NOR2 | 11 | 7.271913e-08 | 7.181833e-08 | -9.014976e-10 | 0.7349 | 2.6207 |
| AND2 | 00 | 2.420113e-07 | 2.433122e-07 | 1.616375e-09 | 0.8235 | 1.8255 |
| AND2 | 01 | 2.498458e-07 | 2.492280e-07 | -1.369970e-09 | 0.6033 | 2.0478 |
| AND2 | 10 | 2.137940e-07 | 2.133515e-07 | -2.879687e-10 | 0.6401 | 1.6787 |
| AND2 | 11 | 3.482361e-07 | 3.480085e-07 | -1.256520e-09 | 0.6003 | 2.0655 |
| OR2 | 00 | 3.391178e-07 | 3.377647e-07 | -3.437405e-09 | 0.8445 | 3.3445 |
| OR2 | 01 | 2.760295e-07 | 2.745233e-07 | 8.055628e-10 | 0.7525 | 1.8451 |
| OR2 | 10 | 2.083101e-07 | 2.073772e-07 | 2.590061e-10 | 0.6372 | 2.0598 |
| OR2 | 11 | 1.804283e-07 | 1.793401e-07 | -8.529779e-10 | 0.6827 | 3.1611 |

## Four baseline algorithm families

These 16 validation results use the common original dataset and split; later neural variants are compared separately.

| Case | Method | R2 | Median error % | 95th percentile % |
|---|---|---:|---:|---:|
| nmos_on | polynomial_ridge | 0.987943 | 6.3518 | 27.5412 |
| nmos_on | extra_trees | 0.935164 | 11.6478 | 67.2695 |
| nmos_on | hist_gradient_boosting | 0.986489 | 4.5646 | 31.7824 |
| nmos_on | neural_network | 0.994103 | 4.9986 | 19.0619 |
| nmos_off | polynomial_ridge | 0.212769 | 15.5670 | 106.0236 |
| nmos_off | extra_trees | 0.673163 | 14.2198 | 69.3382 |
| nmos_off | hist_gradient_boosting | 0.952016 | 4.2762 | 41.5318 |
| nmos_off | neural_network | 0.903005 | 3.2756 | 18.9904 |
| pmos_on | polynomial_ridge | 0.981610 | 5.8540 | 23.4999 |
| pmos_on | extra_trees | 0.955414 | 10.4858 | 58.4307 |
| pmos_on | hist_gradient_boosting | 0.992695 | 4.0304 | 29.1222 |
| pmos_on | neural_network | 0.995543 | 3.9421 | 13.8027 |
| pmos_off | polynomial_ridge | 0.644409 | 14.9814 | 103.5366 |
| pmos_off | extra_trees | 0.807229 | 13.4382 | 64.5922 |
| pmos_off | hist_gradient_boosting | 0.912744 | 4.1401 | 44.4147 |
| pmos_off | neural_network | 0.855855 | 3.1726 | 16.5369 |

## Figures

![Required transistor physical trend plots](checks/physical_trends.png)

![nmos_on held-out test parity](final_results/nmos_on_parity.png)

![nmos_off held-out test parity](final_results/nmos_off_parity.png)

![pmos_on held-out test parity](final_results/pmos_on_parity.png)

![pmos_off held-out test parity](final_results/pmos_off_parity.png)

![All 3600 original gate predictions against SPICE](final_results/gate_parity.png)

## Corner-level error analysis and limitations

The largest mean error across all 18 gate/input cases at one original corner was corner 17: 3.343% at 77.81 °C, VDD 0.9434 V and NMOS vth0 0.31642 V. Other high-error corners include 29 (2.381%, 103.62 °C, NMOS vth0 0.30937 V) and 161 (2.337%, 105.62 °C, NMOS vth0 0.31131 V). The worst gate/input combination by mean error is identified in the gate analysis above. These observations suggest sensitivity to hot corners and low NMOS threshold; they do not establish a single cause.

Uniform transistor sampling sparsely covers exact supply rails used by logic gates. Current magnitudes span many orders, and some individual transistor body-current tails remain harder to fit than the overall median. The refined models use physical current conservation, signed current reconstruction, width normalization and logarithmic targets; future improvement would use better transistor-only validation near these operating conditions while respecting the prescribed sampling distribution. Gate internal voltages are supplied by SPICE in Part B, so this validation does not test an independent voltage predictor. The course-defined Part C circuit and its comparison remain outside this Part A/B report.

Current-conserving refinement: ConservingModel predicts positive conductance (Id-Is)/(2*(Vd-Vs)), gate-current magnitude and body-current magnitude in logarithmic space, normalized by width. Current directions follow the prescribed biases. Drain/source coordinates are canonically sorted; reconstructed currents obey Id+Ig+Is+Ib=0. Inputs exclude the singular log(abs(Vd-Vs)) feature. A 64x64 tanh MLP uses input and target standardization, L-BFGS, alpha=1e-7, fixed seed 20261125 and four checkpointed stages of up to 1500 iterations. Only uniform transistor training rows are fitted; transistor validation median error selects the stage. Run refine_conserving.py after refine_uniform.py and before finalization.


Additional refinement: 10,000 independently uniform single-transistor samples per case are saved in uniform_refined, split 70/15/15. Original 10,000-row datasets and splits are preserved. Supplemental training uses only training rows; selection uses transistor validation data. No gate current labels are fitted. Run refine_uniform.py before finalization to reproduce the expanded experiment. See uniform_refined/*_metrics.json for validation histories and supplementary test errors.

---

## Part C — Implementation handoff

## Assignment and current state

- Team: Triode. Use the supplied `45nm_MGK` transistor model, nominal VDD = 1 V, and the assigned **3-bit carry-lookahead adder (CLA)**.
- Parts A and B have saved datasets, four selected transistor models, five transistor-level gate designs, 200 shared Part B corners, gate predictions and comparison results. Part C has **not** been run.
- The Part B AND2/OR2 second-stage inverter uses the ON/OFF model's logic-rail gate voltage as an approximation to its recorded internal gate voltage; see `PART_AB_REVIEW.md`. Keep this distinction when describing the method.
- Measured Part B mean absolute percentage error is 0.9649% over the original 3,600 gate evaluations and 0.8813% on a fresh 3,600-evaluation check. These are gate results, not CLA results.

## Open these files first

1. `source_documents/DVD_ML_Project.pdf`: official instructions, especially Part C in Section 3, the test-circuit paragraph in Section 5, and deliverables 8–10 in Section 6.
2. `PART_AB_REVIEW.md`: what was done, model choices, metrics, and results for the report.
3. `gates.py`: `devices(gate)` defines transistor connectivity and sizes for INV, NAND2, NOR2, AND2, OR2. `predict(result, models)` computes a gate's leakage from the four transistor models and recorded SPICE node voltages. Read these two functions before constructing the CLA.
4. `gates/corners.json`: **the exact 200 corners to reuse**. Keep the array order and corner indices 0–199. `gates/reference.json` has one Part B gate result for each gate, input pattern and corner, including node voltages and conditions.
5. `selected_models/{nmos_on,nmos_off,pmos_on,pmos_off}.joblib`: frozen final transistor models. Load them with `joblib.load` on the same Python/scikit-learn environment. Their custom model classes are defined in `conserving_model.py`, `independent_model.py`, and `normalized_model.py`; `train_models.py` supplies input features.
6. `models/45nm_MGK.pm`: the transistor parameters for every CLA SPICE run. `gates/INV_0.cir`, `gates/NAND2_00.cir`, etc. are example gate netlists and show the required SPICE options and syntax.

## What to build

1. Decide and document the 3-bit CLA's inputs and equations before coding. If it has `A2..A0`, `B2..B0`, and `Cin`, that is seven binary inputs and **128 input vectors**. If your course explicitly fixes `Cin`, follow that instruction and state it. Do not silently omit `Cin`.
2. Draw a gate graph for propagate, generate, carries and sums. Use **only** the five validated gate types listed above. For example, construct XOR and any wider AND/OR operations from those gates, rather than treating XOR3 or AOI as a new prevalidated model. Label every intermediate net and verify the truth table against ordinary binary addition.
3. Generate one **complete transistor-level CLA netlist** using the same gate transistor connections, `L=45n`, `Wn=90n`, `Wp=180n`, the supplied model and these options in every run: `.options gmin=1e-18 abstol=1e-18 reltol=1e-6 vntol=1e-9`. At each corner, all NMOS share that corner's NMOS parameter draw and all PMOS share its PMOS draw. Apply the binary external inputs at exactly 0 or that corner's VDD. Simulate every input vector at all 200 corners with ngspice and record the complete circuit leakage and output bits. Do not obtain the SPICE reference by summing separate gate SPICE runs.
4. For hierarchical ML, calculate the Boolean input bits at **every gate** in the CLA graph. Look up the matching Part B gate/input/corner record in `gates/reference.json` for its saved internal/output voltages and conditions, and call `gates.predict(record, loaded_models)` to obtain that gate's predicted leakage. Sum the individual gate predictions as the PDF directs. This uses the gate method and the four transistor models; it does not fit on circuit reference currents. The Part B gate voltages are reused at matching logic inputs and corners, consistent with the PDF's stated rail-input, no-loading approximation for Part C.
5. Compare the hierarchical ML sum with the complete CLA SPICE result **for each vector and corner**. Keep the same current convention as Part B: total positive-rail static current, including high external input-source currents. Also save VDD-only results separately if useful, but do not mix conventions in one accuracy calculation.
6. Produce the required CLA results: per-input-vector SPICE median, ML median, bias, median percentage error and 95th-percentile error; a log-axis ML-versus-SPICE parity plot; overall error; a comparison with Part B's gate accuracy; and a short analysis of the largest errors and corner conditions. Percentage error used in Parts A/B was `100*abs(ML-SPICE)/max(abs(SPICE),1e-18 A)` for each run, then aggregated. Report the actual CLA result even if it is less accurate than Part B.
7. Add the CLA netlist, fixed-seed generation/evaluation code, results, figure and explanation to the final report/package. Parts A/B should remain frozen while Part C is developed. Do Part C work in a copy of the extracted folder or new files, leaving the supplied evidence intact.

## Existing results: examples, not CLA measurements

- `final_results/gate_predictions.csv`: 3,600 existing Part B SPICE and ML gate values, indexed by gate, input bits and corner.
- `final_results/gate_metrics.csv`, `final_results/gate_parity.png`: Part B table and plot.
- `final_results/gate_node_voltages.csv`: the SPICE voltages supplied to Part B ML. This is not an independently predicted voltage set.
- `final_results/transistor_metrics.json`, `final_results/four_method_comparison.csv`: Part A results.
- `checks/part_ab_audit.json`: completed automated checks for Parts A/B.
- `fresh_evaluation/`: separate extra gate-corner validation. **Do not use these fresh corners for the required Part C comparison**; use `gates/corners.json`.

## Environment and checks

- Original runs used ngspice 45.2 and Python with NumPy, SciPy, scikit-learn 1.7.2, joblib and Matplotlib. Saved joblib files should be loaded with a compatible scikit-learn version.
- First test the CLA logic on all input vectors, then test one SPICE corner/vector, then the matching hierarchical ML calculation, and only then run the full set. This catches wiring, sign and indexing mistakes early.
- Keep `gate`, `bits`, `corner`, `input_vector`, `spice`, `ml`, and output bits in saved result rows. Check row counts: with seven independent inputs, expect `128*200 = 25,600` complete-circuit SPICE results and ML predictions.
- Do not train or tune the transistor models using the Part B gate references or the Part C complete-circuit reference currents.

---
# Part C — ML-Driven PVT Variation-Aware Leakage Estimation

## Overview

Part C evaluates a hierarchical machine-learning (ML) leakage estimator for a transistor-level 3-bit carry-lookahead adder (CLA). The ML estimate is compared against full-circuit SPICE leakage simulations across input vectors and process-voltage-temperature (PVT) corners.

The design uses the **45 nm MGK technology** and a **nominal supply voltage of 1 V**.

## Methodology

### 1. Input vectors and PVT corners

- The CLA has seven binary inputs: `A[2:0]`, `B[2:0]`, and `Cin`.
- All \(2^7 = 128\) input combinations are evaluated.
- The evaluation uses 200 PVT corners.
- Total evaluation points: **128 × 200 = 25,600**.

### 2. Full-circuit SPICE reference

For each input vector and PVT corner, the complete transistor-level CLA test circuit is simulated in SPICE. Its leakage result is used as the reference value.

This is a full-circuit simulation; the reference is not obtained by simply adding separately simulated gate leakages.

### 3. Hierarchical ML leakage estimate

For each input vector:

1. Determine the Boolean value at each gate in the CLA.
2. Use the corresponding Part B gate leakage model to estimate the leakage of each gate at the selected PVT corner and input state.
3. Sum the gate leakage estimates to obtain the hierarchical ML estimate for the CLA.

The ML estimate is compared with the full-circuit SPICE reference for every evaluation point.

## Evaluation metrics

For each run, the absolute percentage error is calculated as

\[
E_i(\%) =
100\frac{|ML_i-SPICE_i|}
{\max(|SPICE_i|,10^{-18}\ \mathrm{A})}.
\]

The **Mean Absolute Percentage Error (MAPE)** is the mean of these per-run absolute percentage errors:

\[
MAPE=\frac{1}{N}\sum_{i=1}^{N}E_i.
\]

For this project, mean accuracy is reported as

\[
\mathrm{Mean\ Accuracy}=100\%-MAPE.
\]

## Part C — Final results

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
