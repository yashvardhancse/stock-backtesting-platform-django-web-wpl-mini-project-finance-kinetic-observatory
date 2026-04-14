from __future__ import annotations

import json
from typing import Sequence

import pandas as pd


def dataframe_records(frame: pd.DataFrame, columns: Sequence[str] | None = None) -> list[dict]:
    """Return JSON-safe records for API payloads and templates."""

    working_frame = frame.copy()
    if columns is not None:
        working_frame = working_frame.loc[:, list(columns)]

    datetime_columns = [
        column for column in working_frame.columns if pd.api.types.is_datetime64_any_dtype(working_frame[column])
    ]
    for column in datetime_columns:
        working_frame[column] = pd.to_datetime(working_frame[column]).dt.strftime("%Y-%m-%d %H:%M:%S")

    return json.loads(working_frame.to_json(orient="records", date_format="iso"))
