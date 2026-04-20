from __future__ import annotations

from django import forms
import pandas as pd


STRATEGY_CHOICES = [
    ("ma", "Moving Average"),
    ("rsi", "RSI"),
    ("ema", "EMA"),
]

REQUIRED_COLUMNS_LOWER = ["date", "open", "high", "low", "close", "volume"]


def normalize_columns(df):
    df.columns = [str(col).strip().lower() for col in df.columns]

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

    df = df.rename(columns=column_map)
    return df


class DatasetUploadForm(forms.Form):
    dataset_file = forms.FileField(
        label="Excel file (.xlsx)",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control kinetic-input",
                "accept": ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        ),
    )
    label = forms.CharField(
        label="Dataset label",
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control kinetic-input", "placeholder": "e.g. NIFTY April Sample"}
        ),
    )

    def clean_dataset_file(self):
        uploaded_file = self.cleaned_data["dataset_file"]
        file_name = uploaded_file.name.lower()

        if not file_name.endswith(".xlsx"):
            raise forms.ValidationError(
                "Only Excel .xlsx files are supported."
            )

        try:
            df = pd.read_excel(uploaded_file)
            df = normalize_columns(df)
            print("Uploaded columns:", df.columns.tolist())

            for column in REQUIRED_COLUMNS_LOWER:
                if column not in df.columns:
                    raise forms.ValidationError(f"Missing column: {column}")
        except Exception as e:
            if isinstance(e, forms.ValidationError):
                raise
            raise forms.ValidationError(f"Error reading file: {str(e)}")

        uploaded_file.seek(0)
        return uploaded_file


class BacktestConfigForm(forms.Form):
    strategy = forms.ChoiceField(
        choices=STRATEGY_CHOICES,
        initial="ma",
        widget=forms.Select(attrs={"class": "form-select kinetic-input", "id": "strategy"}),
    )
    short_window = forms.IntegerField(
        initial=9,
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    long_window = forms.IntegerField(
        initial=21,
        min_value=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    rsi_period = forms.IntegerField(
        initial=14,
        min_value=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    ema_window = forms.IntegerField(
        initial=20,
        min_value=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        strategy = cleaned_data.get("strategy")
        short_window = cleaned_data.get("short_window")
        long_window = cleaned_data.get("long_window")
        rsi_period = cleaned_data.get("rsi_period")
        ema_window = cleaned_data.get("ema_window")

        if strategy == "ma":
            if not short_window or not long_window:
                raise forms.ValidationError("Short window and long window are required for Moving Average.")
            if short_window >= long_window:
                raise forms.ValidationError("Short window must be lower than the long window.")

        if strategy == "rsi" and not rsi_period:
            raise forms.ValidationError("RSI period is required for RSI strategy.")

        if strategy == "ema" and not ema_window:
            raise forms.ValidationError("EMA window is required for EMA strategy.")

        return cleaned_data
