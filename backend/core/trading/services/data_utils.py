from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.conf import settings

REQUIRED_OHLCV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
REQUIRED_OHLCV_COLUMNS_LOWER = ["date", "open", "high", "low", "close", "volume"]


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize incoming dataset headers and map common aliases."""

    frame.columns = [str(column).strip().lower() for column in frame.columns]

    column_map = {
        "timestamp": "date",
        "datetime": "date",
        "time": "date",
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    }

    frame = frame.rename(columns=column_map)
    # If multiple aliases map to the same final name, keep the first occurrence.
    frame = frame.loc[:, ~frame.columns.duplicated()]
    return frame


@dataclass(frozen=True)
class DatasetValidationResult:
    """Structured feedback for dataset validation failures."""

    is_valid: bool
    errors: list[str]


def _read_dataset_frame(file_obj) -> pd.DataFrame:
    """Read .xlsx input into a DataFrame."""

    file_name = getattr(file_obj, "name", "").lower()

    if file_name.endswith(".xlsx"):
        return pd.read_excel(file_obj)

    raise ValueError("Only Excel .xlsx uploads are supported.")


def validate_uploaded_dataset(file_obj) -> DatasetValidationResult:
    """Validate uploaded file type and required OHLCV schema."""

    file_name = getattr(file_obj, "name", "").lower()
    errors: list[str] = []

    if not file_name.endswith(".docx"):
        errors.append("Only Excel .xlsx uploads are supported.")

    try:
        frame = _read_dataset_frame(file_obj)
    except Exception as exc:  # pragma: no cover - defensive guard for malformed files
        errors.append(f"Unable to parse dataset file: {exc}")
        return DatasetValidationResult(is_valid=False, errors=errors)

    frame = normalize_columns(frame)
    print("Uploaded columns:", frame.columns.tolist())
    missing_columns = [column for column in REQUIRED_OHLCV_COLUMNS_LOWER if column not in frame.columns]
    if missing_columns:
        errors.append("Missing required columns: " + ", ".join(missing_columns))

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    return DatasetValidationResult(is_valid=not errors, errors=errors)


def handle_upload(file_obj) -> dict:
    """Read Excel upload, validate OHLCV columns, and persist media/latest.csv."""

    try:
        frame = pd.read_excel(file_obj)
        frame = normalize_columns(frame)
        print("Uploaded columns:", frame.columns.tolist())

        for column in REQUIRED_OHLCV_COLUMNS_LOWER:
            if column not in frame.columns:
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)
                return {"error": f"Missing column: {column}"}

        cleaned_frame = frame[REQUIRED_OHLCV_COLUMNS_LOWER].copy()
        cleaned_frame["date"] = pd.to_datetime(cleaned_frame["date"], errors="coerce")
        for column in ["open", "high", "low", "close", "volume"]:
            cleaned_frame[column] = pd.to_numeric(cleaned_frame[column], errors="coerce")

        cleaned_frame = (
            cleaned_frame.dropna(subset=REQUIRED_OHLCV_COLUMNS_LOWER)
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        if cleaned_frame.empty:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            return {"error": "Uploaded file has no valid rows after cleaning."}

        cleaned_frame.columns = [column.capitalize() for column in cleaned_frame.columns]

        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        latest_csv_path = media_root / "latest.csv"
        cleaned_frame.to_csv(latest_csv_path, index=False)

        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        return {
            "success": True,
            "cleaned_frame": cleaned_frame,
            "latest_csv_path": str(latest_csv_path),
        }
    except Exception as exc:  # pragma: no cover - defensive guard for malformed files
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        return {"error": str(exc)}


# Backward-compatible alias retained for older imports.
validate_uploaded_csv = validate_uploaded_dataset


def load_clean_dataset(file_obj) -> pd.DataFrame:
    """Load, standardize, and chronologically sort an OHLCV dataset."""

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    frame = _read_dataset_frame(file_obj)
    frame = normalize_columns(frame)
    print("Uploaded columns:", frame.columns.tolist())

    missing_columns = [column for column in REQUIRED_OHLCV_COLUMNS_LOWER if column not in frame.columns]
    if missing_columns:
        raise ValueError("Missing required columns: " + ", ".join(missing_columns))

    renamed_frame = frame[REQUIRED_OHLCV_COLUMNS_LOWER].copy()
    renamed_frame["date"] = pd.to_datetime(renamed_frame["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        renamed_frame[column] = pd.to_numeric(renamed_frame[column], errors="coerce")

    cleaned_frame = (
        renamed_frame.dropna(subset=REQUIRED_OHLCV_COLUMNS_LOWER)
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    cleaned_frame.columns = [column.capitalize() for column in cleaned_frame.columns]
    cleaned_frame["Returns"] = cleaned_frame["Close"].pct_change().fillna(0.0)

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    return cleaned_frame
