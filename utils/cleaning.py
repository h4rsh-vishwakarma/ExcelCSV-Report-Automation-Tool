"""Dataset-agnostic cleaning helpers: works on any reasonably-structured CSV/Excel."""

import re
import numpy as np
import pandas as pd


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    new_cols = []
    seen = {}
    for col in df.columns:
        name = str(col).strip()
        name = re.sub(r"[^\w]+", "_", name)
        name = re.sub(r"_+", "_", name).strip("_").lower()
        if not name:
            name = "column"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        new_cols.append(name)
    df.columns = new_cols
    return df


def _try_parse_dates(series: pd.Series) -> pd.Series | None:
    if series.dtype != object:
        return None
    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return None
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    if parsed.notna().mean() >= 0.8:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    return None


def _try_parse_numeric(series: pd.Series) -> pd.Series | None:
    if series.dtype != object:
        return None
    cleaned = series.astype(str).str.replace(r"[,$%\s]", "", regex=True)
    numeric = pd.to_numeric(cleaned, errors="coerce")
    valid_mask = series.notna()
    if valid_mask.sum() == 0:
        return None
    if numeric[valid_mask].notna().mean() >= 0.9:
        return numeric
    return None


def fix_dtypes(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Detect numbers/dates stored as text and convert them. Returns (df, changes)."""
    df = df.copy()
    changes = {}
    for col in df.columns:
        numeric = _try_parse_numeric(df[col])
        if numeric is not None:
            df[col] = numeric
            changes[col] = "converted to numeric"
            continue
        dates = _try_parse_dates(df[col])
        if dates is not None:
            df[col] = dates
            changes[col] = "converted to datetime"
    return df, changes


def remove_duplicate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    return df, removed


def handle_missing_values(df: pd.DataFrame, strategy: str = "fill") -> tuple[pd.DataFrame, dict]:
    """strategy: 'drop_rows', 'fill', or 'leave'."""
    df = df.copy()
    missing_before = df.isna().sum()
    missing_before = missing_before[missing_before > 0].to_dict()

    if strategy == "drop_rows":
        df = df.dropna()
    elif strategy == "fill":
        for col in df.columns:
            if df[col].isna().sum() == 0:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].ffill().bfill()
            else:
                mode = df[col].mode(dropna=True)
                fill_val = mode.iloc[0] if not mode.empty else "Unknown"
                df[col] = df[col].fillna(fill_val)
    # 'leave' does nothing

    return df, missing_before


def detect_column_types(df: pd.DataFrame) -> dict:
    numeric_cols, date_cols, categorical_cols = [], [], []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)
    return {"numeric": numeric_cols, "date": date_cols, "categorical": categorical_cols}


def clean_dataframe(df: pd.DataFrame, missing_strategy: str = "fill") -> tuple[pd.DataFrame, dict]:
    """Run the full cleaning pipeline. Returns (cleaned_df, report)."""
    report = {}

    df = standardize_column_names(df)

    df, dtype_changes = fix_dtypes(df)
    report["dtype_changes"] = dtype_changes

    df, missing_before = handle_missing_values(df, missing_strategy)
    report["missing_values_found"] = missing_before
    report["missing_strategy"] = missing_strategy

    df, duplicates_removed = remove_duplicate_rows(df)
    report["duplicates_removed"] = duplicates_removed

    df = df.reset_index(drop=True)
    return df, report


def build_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Generic summary stats table that works for any dataset."""
    rows = []
    for col in df.columns:
        s = df[col]
        row = {
            "column": col,
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "nulls": int(s.isna().sum()),
            "unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            row.update({
                "mean": round(s.mean(), 2) if s.notna().any() else None,
                "median": round(s.median(), 2) if s.notna().any() else None,
                "min": s.min() if s.notna().any() else None,
                "max": s.max() if s.notna().any() else None,
                "std": round(s.std(), 2) if s.notna().any() else None,
            })
        elif pd.api.types.is_datetime64_any_dtype(s):
            row.update({
                "min": s.min() if s.notna().any() else None,
                "max": s.max() if s.notna().any() else None,
            })
        else:
            top = s.mode(dropna=True)
            row.update({"top_value": top.iloc[0] if not top.empty else None})
        rows.append(row)
    return pd.DataFrame(rows)
