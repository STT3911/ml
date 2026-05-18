# Behavioral Session Identification

This project implements the practical part of the coursework:

"Identification and verification of a user using VPN/Proxy based on behavioral biometrics and temporal network sessions."

## What is implemented

- flow-level sessionization with inactivity thresholds
- session-level feature extraction
- hybrid model:
  - user classifier
  - per-user anomaly detector
- evaluation scenarios:
  - `direct -> vpn`
  - `mixed`
  - `open-set`
- synthetic data generator for demo runs without a real dataset

## Expected input CSV

The pipeline expects flow records with these columns:

- `user_id`
- `mode`
- `start_time`
- `end_time`
- `duration`
- `bytes_up`
- `bytes_down`
- `pkts_up`
- `pkts_down`

Optional columns improve the model:

- `flow_iat_mean`, `flow_iat_std`, `flow_iat_min`, `flow_iat_max`
- `fwd_iat_mean`, `fwd_iat_std`, `fwd_iat_min`, `fwd_iat_max`
- `bwd_iat_mean`, `bwd_iat_std`, `bwd_iat_min`, `bwd_iat_max`
- `active_mean`, `active_std`, `active_min`, `active_max`
- `idle_mean`, `idle_std`, `idle_min`, `idle_max`
- `bytes_per_sec`
- `pkts_per_sec`

## Install

```powershell
python -m pip install -r requirements.txt
```

If you want the exact classifier from the coursework baseline, also install:

```powershell
python -m pip install catboost
```

## Run demo on synthetic data

```powershell
python scripts/run_demo.py --output-dir artifacts/demo
```

## Run VPN/non-VPN classification on ISCX ARFF data

The downloaded ISCX-VPN-NonVPN ARFF files do not contain `user_id` or flow timestamps,
so they should not be used for user identification directly. For this real dataset,
run the methodologically correct task: binary VPN/non-VPN detection from time-based
flow features.

Place the ARFF files in `data/`, then run:

```powershell
python scripts/run_iscx_vpn.py --data-dir data --output-dir artifacts/iscx_vpn
```

The script evaluates each combined time window file, for example `15s`, `30s`,
`60s`, and `120s`.

## Run on your own dataset

```powershell
python scripts/run_demo.py --input-csv data/flows.csv --output-dir artifacts/real_run
```

## Outputs

The script writes:

- `session_features.csv`
- `metrics.json`
- `predictions_<scenario>.csv`
- plots:
  - confusion matrix
  - ROC curve
  - quality drop summary

For ISCX VPN/non-VPN runs, the script writes:

- `metrics_comparison.csv`
- per-window `metrics_summary.csv`
- `predictions.csv`
- `feature_importance.csv`
- `model.joblib`
- converted ARFF snapshots
- confusion matrix, ROC, precision-recall, feature-importance, correlation,
  class-distribution, probability-distribution, and application-error plots

## Build coursework document

After running the demo and ISCX experiments, build the final coursework files:

```powershell
python scripts/build_coursework.py
```

Outputs:

- `artifacts/coursework/coursework_final.docx`
- `artifacts/coursework/coursework_final.md`

## Proxy user-identification experiment on ISCX

ISCX ARFF files have no `user_id`, so a strict user-identification experiment
is impossible on this dataset. As a methodological proxy, the script below
treats each application class (BROWSING, VOIP, CHAT, ...) as a "behavioral
identity". It tests the same hypothesis the user-ID task tests — whether
time-based flow features preserve behavioral identity through a VPN tunnel —
but the identities are application behaviors, not individual users. Numbers
must not be presented as user-level identification accuracy. The script
writes a `DISCLAIMER.txt` next to the metrics.

```powershell
python scripts/run_iscx_userid_proxy.py --input-arff data/TimeBasedFeatures-Dataset-15s.arff --output-dir artifacts/iscx_userid_proxy
```

Outputs:

- `metrics_summary.csv` and `metrics.json` for the three scenarios
  (`direct_to_vpn`, `mixed`, `open_set`)
- per-scenario `predictions_*.csv`
- confusion matrices and per-application accuracy plot
- `DISCLAIMER.txt` with the proxy caveat

## Test a saved ISCX model

After training, test the saved model without retraining:

```powershell
python scripts/predict_iscx_vpn.py --model artifacts/iscx_vpn/15s/model.joblib --input-arff data/TimeBasedFeatures-Dataset-15s.arff --output-csv artifacts/iscx_vpn/manual_test_predictions.csv
```

Use this as a technical load-and-predict check. For unbiased quality numbers,
use `artifacts/iscx_vpn/metrics_comparison.csv`.

## Notes

- The default session threshold is 60 minutes.
- The script also evaluates a 30-minute split as a comparison point.
- If `catboost` is not installed, the pipeline falls back to `RandomForestClassifier`.
