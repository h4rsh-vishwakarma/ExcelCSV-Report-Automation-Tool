import io

import pandas as pd
import streamlit as st

from utils.cleaning import clean_dataframe, detect_column_types, build_summary_stats
from utils.charts import auto_generate_charts
from utils.report import build_excel_report, build_pdf_report

st.set_page_config(page_title="Excel/CSV Report Automation Tool", layout="wide")

SAMPLE_PATH = "sample_data/sample_sales.csv"


@st.cache_data
def load_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    return pd.read_excel(io.BytesIO(file_bytes))


@st.cache_data
def render_chart_images(_charts):
    images = []
    for key, fig in _charts:
        try:
            images.append((fig.layout.title.text or key, fig.to_image(format="png", width=900, height=500, scale=2)))
        except Exception:
            pass
    return images


def main():
    st.title("📊 Excel/CSV Report Automation Tool")
    st.caption("Upload a messy spreadsheet → get cleaned data, auto charts, and a client-ready report.")

    with st.sidebar:
        st.header("⚙️ Options")
        missing_strategy = st.selectbox(
            "How to handle missing values",
            options=["fill", "drop_rows", "leave"],
            format_func=lambda x: {
                "fill": "Fill (median / mode)",
                "drop_rows": "Drop rows with missing data",
                "leave": "Leave as-is",
            }[x],
        )
        row_limit_warning = st.number_input("Warn if row count exceeds", min_value=1000, value=200_000, step=1000)
        st.divider()
        use_sample = st.button("🧪 Try with sample data")

    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

    file_bytes, filename = None, None
    if use_sample:
        with open(SAMPLE_PATH, "rb") as f:
            file_bytes = f.read()
        filename = "sample_sales.csv"
        st.session_state["_source_name"] = "sample_sales"
    elif uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name
        st.session_state["_source_name"] = filename.rsplit(".", 1)[0]

    if file_bytes is None:
        st.info("Upload a file, or click **Try with sample data** in the sidebar to see it in action.")
        return

    try:
        raw_df = load_file(file_bytes, filename)
    except Exception as e:
        st.error(f"Couldn't read this file: {e}")
        return

    if raw_df.empty:
        st.warning("The uploaded file has no rows.")
        return
    if len(raw_df) > row_limit_warning:
        st.warning(f"This file has {len(raw_df):,} rows — processing may be slow.")

    st.subheader("1. Raw data preview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(raw_df):,}")
    c2.metric("Columns", len(raw_df.columns))
    c3.metric("Missing cells", int(raw_df.isna().sum().sum()))
    st.dataframe(raw_df.head(20), use_container_width=True)

    cleaned_df, clean_report = clean_dataframe(raw_df, missing_strategy=missing_strategy)
    column_types = detect_column_types(cleaned_df)
    stats_df = build_summary_stats(cleaned_df)

    st.subheader("2. Cleaned data")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Rows", f"{len(cleaned_df):,}", delta=f"{len(cleaned_df) - len(raw_df)}")
    cc2.metric("Duplicates removed", clean_report["duplicates_removed"])
    cc3.metric("Columns retyped", len(clean_report["dtype_changes"]))
    with st.expander("What changed"):
        if clean_report["dtype_changes"]:
            st.write("**Type fixes:**", clean_report["dtype_changes"])
        else:
            st.write("**Type fixes:** none needed")
        if clean_report["missing_values_found"]:
            st.write("**Missing values found (before handling):**", clean_report["missing_values_found"])
        else:
            st.write("**Missing values found:** none")
    st.dataframe(cleaned_df.head(20), use_container_width=True)

    st.subheader("3. Summary statistics")
    st.dataframe(stats_df, use_container_width=True)

    st.subheader("4. Auto-generated charts")
    charts = auto_generate_charts(cleaned_df, column_types)
    if not charts:
        st.info("No chart-friendly columns detected in this dataset.")
    else:
        cols = st.columns(2)
        for i, (key, fig) in enumerate(charts):
            cols[i % 2].plotly_chart(fig, use_container_width=True, key=key)

    st.subheader("5. Download")
    d1, d2, d3 = st.columns(3)

    d1.download_button(
        "⬇️ Cleaned CSV",
        data=cleaned_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{st.session_state['_source_name']}_cleaned.csv",
        mime="text/csv",
    )

    excel_bytes = build_excel_report(raw_df, cleaned_df, stats_df, clean_report)
    d2.download_button(
        "⬇️ Excel report (.xlsx)",
        data=excel_bytes,
        file_name=f"{st.session_state['_source_name']}_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if d3.button("📄 Generate PDF report"):
        with st.spinner("Rendering charts and building PDF..."):
            chart_images = render_chart_images(charts)
            pdf_bytes = build_pdf_report(
                cleaned_df, stats_df, clean_report, chart_images,
                source_name=st.session_state["_source_name"],
            )
        st.download_button(
            "⬇️ Download PDF report",
            data=pdf_bytes,
            file_name=f"{st.session_state['_source_name']}_report.pdf",
            mime="application/pdf",
        )


if __name__ == "__main__":
    main()
