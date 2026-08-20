# Excel/CSV Report Automation Tool

Upload a messy CSV/Excel file and get back cleaned data, auto-generated charts, and a client-ready Excel/PDF report — in seconds.

## Features

- Upload `.csv` / `.xlsx` / `.xls`, preview raw data (shape, dtypes, missing values)
- Automatic cleaning: standardizes column names, fixes numbers/dates stored as text, removes duplicates, handles missing values (fill / drop / leave — configurable)
- Dataset-agnostic summary statistics (works on any reasonably-structured file, not hardcoded to one schema)
- Auto-generated charts based on detected column types: numeric distributions, categorical breakdowns, date trend lines
- Export: cleaned CSV, multi-sheet Excel report (Overview / Cleaned Data / Raw Data / Summary Stats), PDF summary report with embedded charts
- "Try with sample data" button for instant demos

## Project structure

```
app.py                     Streamlit UI
utils/cleaning.py          Column standardization, dtype fixes, missing values, dedup, summary stats
utils/charts.py            Auto chart generation (Plotly)
utils/report.py            Excel + PDF report builders
sample_data/sample_sales.csv  Sample messy dataset for demos
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → connect the repo → set `app.py` as the entry point
3. Deploy — live in a couple of minutes

## Notes

- PDF export uses `kaleido` to rasterize Plotly charts to PNG; if chart rendering fails in a locked-down environment, the Excel report is the reliable fallback.
- Free-tier Streamlit Cloud apps sleep after inactivity — first load after idle takes a few seconds to wake up.
