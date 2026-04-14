from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REQUIRED_OHLCV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class DatasetValidationResult:
    """Structured feedback for dataset validation failures."""

    is_valid: bool
    errors: list[str]


def _read_dataset_frame(file_obj) -> pd.DataFrame:
    """Read CSV or Excel input into a DataFrame."""

    file_name = getattr(file_obj, "name", "").lower()

    if file_name.endswith(".csv"):
        return pd.read_csv(file_obj)

    if file_name.endswith(".xlsx"):
        return pd.read_excel(file_obj, engine="openpyxl")

    if file_name.endswith(".xls"):
        return pd.read_excel(file_obj, engine="xlrd")

    raise ValueError("Only CSV and Excel uploads are supported.")


def validate_uploaded_csv(file_obj) -> DatasetValidationResult:
    """Validate uploaded file type and required OHLCV schema."""

    file_name = getattr(file_obj, "name", "").lower()
    errors: list[str] = []

    if not file_name.endswith((".csv", ".xlsx", ".xls")):
        errors.append("Only CSV and Excel uploads are supported.")

    try:
        frame = _read_dataset_frame(file_obj)
    except Exception as exc:  # pragma: no cover - defensive guard for malformed files
        errors.append(f"Unable to parse dataset file: {exc}")
        return DatasetValidationResult(is_valid=False, errors=errors)

    normalized_columns = {str(column).strip().lower(): column for column in frame.columns}
    missing_columns = [column for column in REQUIRED_OHLCV_COLUMNS if column.lower() not in normalized_columns]
    if missing_columns:
        errors.append("Missing required columns: " + ", ".join(missing_columns))

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    return DatasetValidationResult(is_valid=not errors, errors=errors)


def load_clean_dataset(file_obj) -> pd.DataFrame:
    """Load, standardize, and chronologically sort an OHLCV dataset."""

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    frame = _read_dataset_frame(file_obj)
    frame.columns = [str(column).strip() for column in frame.columns]
    column_map = {column.lower(): column for column in frame.columns}

    missing_columns = [column for column in REQUIRED_OHLCV_COLUMNS if column.lower() not in column_map]
    if missing_columns:
        raise ValueError("Missing required columns: " + ", ".join(missing_columns))

    renamed_frame = frame.rename(
        columns={column_map[column.lower()]: column for column in REQUIRED_OHLCV_COLUMNS}
    )
    renamed_frame["Date"] = pd.to_datetime(renamed_frame["Date"], errors="coerce")
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        renamed_frame[column] = pd.to_numeric(renamed_frame[column], errors="coerce")

    cleaned_frame = (
        renamed_frame.dropna(subset=REQUIRED_OHLCV_COLUMNS)
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )
    cleaned_frame["Returns"] = cleaned_frame["Close"].pct_change().fillna(0.0)

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    return cleaned_frame
