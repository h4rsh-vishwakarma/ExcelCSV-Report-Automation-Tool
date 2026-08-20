"""Excel + PDF report export."""

import io
import pandas as pd
from fpdf import FPDF


def build_excel_report(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame, stats_df: pd.DataFrame,
                        clean_report: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        cleaned_df.to_excel(writer, sheet_name="Cleaned Data", index=False)
        raw_df.to_excel(writer, sheet_name="Raw Data", index=False)
        stats_df.to_excel(writer, sheet_name="Summary Stats", index=False)

        overview_rows = [
            ("Raw rows", len(raw_df)),
            ("Cleaned rows", len(cleaned_df)),
            ("Columns", len(cleaned_df.columns)),
            ("Duplicate rows removed", clean_report.get("duplicates_removed", 0)),
            ("Missing value strategy", clean_report.get("missing_strategy", "n/a")),
        ]
        overview_df = pd.DataFrame(overview_rows, columns=["Metric", "Value"])
        overview_df.to_excel(writer, sheet_name="Overview", index=False)

        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#4472C4", "font_color": "white"})
        for sheet_name, frame in [
            ("Cleaned Data", cleaned_df), ("Raw Data", raw_df),
            ("Summary Stats", stats_df), ("Overview", overview_df),
        ]:
            ws = writer.sheets[sheet_name]
            for col_idx, col_name in enumerate(frame.columns):
                ws.write(0, col_idx, col_name, header_fmt)
                width = min(max(len(str(col_name)), frame[col_name].astype(str).str.len().max() if len(frame) else 10) + 2, 40)
                ws.set_column(col_idx, col_idx, width)

    return buffer.getvalue()


def _safe_text(text) -> str:
    return str(text).encode("latin-1", "replace").decode("latin-1")


def build_pdf_report(cleaned_df: pd.DataFrame, stats_df: pd.DataFrame, clean_report: dict,
                      chart_images: list, source_name: str = "dataset") -> bytes:
    """chart_images: list of (title, png_bytes)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, _safe_text(f"Report: {source_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Generated automatically from uploaded data", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Overview", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    overview_lines = [
        f"Rows: {len(cleaned_df)}",
        f"Columns: {len(cleaned_df.columns)}",
        f"Duplicate rows removed: {clean_report.get('duplicates_removed', 0)}",
        f"Missing value strategy: {clean_report.get('missing_strategy', 'n/a')}",
    ]
    for line in overview_lines:
        pdf.cell(0, 7, _safe_text(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary Statistics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    cols = list(stats_df.columns)
    col_width = (pdf.w - 20) / len(cols)
    pdf.set_font("Helvetica", "B", 8)
    for c in cols:
        pdf.cell(col_width, 7, _safe_text(c), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for _, row in stats_df.iterrows():
        for c in cols:
            val = row[c]
            text = "" if pd.isna(val) else str(val)
            if len(text) > 18:
                text = text[:15] + "..."
            pdf.cell(col_width, 6, _safe_text(text), border=1)
        pdf.ln()

    for title, img_bytes in chart_images:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
        img_buf = io.BytesIO(img_bytes)
        pdf.image(img_buf, x=10, w=pdf.w - 20)

    return bytes(pdf.output())
