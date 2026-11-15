# Triode handoff: build Part C from the completed Parts A and B

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
