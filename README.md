<<<<<<< HEAD
# Automated Insight Generation — AI/ML Assignment 4

## Overview
A Python-only Streamlit application that loads a district-level healthcare CSV and automatically detects trends, outliers, and strong Pearson correlations. It generates structured, data-driven explanations and provides live filters and visualizations.

## Requirements
- Python 3.10 or newer recommended
- Internet connection for the first installation of Python packages
- VS Code or another terminal

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `automated_insight_generation` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. (Optional but recommended) Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run:
   ```bat
   .venv\Scripts\activate.bat
   ```
5. Install dependencies:
   ```powershell
   py -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   py -m streamlit run app.py
   ```
7. Streamlit will print a local URL, normally `http://localhost:8501`. Open it in your browser.
8. Use the sidebar to filter districts, months and indicators, and adjust trend, outlier and correlation thresholds.
9. Use the download buttons to export the insights CSV and correlation matrix CSV.

## Use your own CSV
Upload a CSV from the sidebar. It must contain these columns:
`month,district,anc_coverage,institutional_delivery,immunization,high_risk_cases`

`month` should be parseable as a date such as `2026-08`. Indicator columns must contain numeric values. Blank or non-numeric indicator values are counted as missing.

## Detection methods
- **Trend:** percentage change between consecutive available months within each district and indicator. Default significant-change threshold: 10%.
- **Outlier:** IQR rule (`Q1 - 1.5×IQR`, `Q3 + 1.5×IQR`) or absolute Z-score threshold (default 3).
- **Correlation:** Pearson correlation matrix; pairs with absolute correlation at least 0.70 are flagged.
- **Severity:** trend severity is Medium at the configured threshold and High at twice the threshold. Outlier severity is derived from relative distance to the indicator median. Correlation severity is High at |r| ≥ 0.90 and Medium otherwise.
- **Insights:** auto-numbered rows with type, indicator, entity, period, value, previous value, percentage change, severity and explanation.

## Limitations
The supplied example has only 12 rows (2 months × 6 districts). Correlation estimates are fragile at this sample size and do not demonstrate causation. The assignment recommends substantially more months and districts for stable trend/correlation analysis. Outlier cutoffs are calculated from the data currently loaded; results can change when more observations are added.
=======
# Automated-Insight-Generation-task
Healthcare analytics dashboard with automated insight generation using Python and Streamlit
>>>>>>> 69761109eed0aa5aebd9eb8c95110b7a3bce12f6
