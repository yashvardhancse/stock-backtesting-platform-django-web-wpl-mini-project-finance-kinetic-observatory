from __future__ import annotations

from django import forms
import pandas as pd


STRATEGY_CHOICES = [
    ("ma_crossover", "Moving Average Crossover"),
    ("rsi", "RSI Strategy"),
    ("vwap", "VWAP Strategy"),
    ("bollinger", "Bollinger Band Strategy"),
    ("macd", "MACD Strategy"),
]

MA_TYPE_CHOICES = [
    ("sma", "SMA"),
    ("ema", "EMA"),
]


class DatasetUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Data file (CSV or Excel)",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control kinetic-input",
                "accept": ".csv,text/csv,.xlsx,.xls,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        ),
    )
    label = forms.CharField(
        label="Dataset label",
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control kinetic-input", "placeholder": "Optional name"}
        ),
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data["csv_file"]
        file_name = uploaded_file.name.lower()
        
        # Check file extension
        if not any(
            file_name.endswith(ext)
            for ext in [".csv", ".xlsx", ".xls"]
        ):
            raise forms.ValidationError(
                "Only CSV and Excel files (.csv, .xlsx, .xls) are supported."
            )
        
        # Validate headers exist
        try:
            if file_name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, nrows=1)
            else:  # Excel file
                df = pd.read_excel(uploaded_file, nrows=1)
            
            required_headers = {"date", "open", "high", "low", "close", "volume"}
            found_headers = set(col.lower() for col in df.columns)
            
            if not required_headers.issubset(found_headers):
                raise forms.ValidationError(
                    f"File must contain headers: {', '.join(required_headers)}"
                )
        except Exception as e:
            if isinstance(e, forms.ValidationError):
                raise
            raise forms.ValidationError(f"Error reading file: {str(e)}")
        
        # Reset file pointer for later reading
        uploaded_file.seek(0)
        return uploaded_file


class BacktestConfigForm(forms.Form):
    strategy = forms.ChoiceField(
        choices=STRATEGY_CHOICES,
        initial="ma_crossover",
        widget=forms.Select(attrs={"class": "form-select kinetic-input"}),
    )
    ma_type = forms.ChoiceField(
        choices=MA_TYPE_CHOICES,
        initial="sma",
        widget=forms.Select(attrs={"class": "form-select kinetic-input"}),
    )
    short_window = forms.IntegerField(
        initial=9,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    long_window = forms.IntegerField(
        initial=21,
        min_value=2,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    rsi_period = forms.IntegerField(
        initial=14,
        min_value=2,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    rsi_oversold = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=49,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    rsi_overbought = forms.IntegerField(
        initial=70,
        min_value=51,
        max_value=99,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    bb_window = forms.IntegerField(
        initial=20,
        min_value=2,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    bb_std_dev = forms.FloatField(
        initial=2.0,
        min_value=0.1,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input", "step": "0.1"}),
    )
    macd_fast = forms.IntegerField(
        initial=12,
        min_value=2,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    macd_slow = forms.IntegerField(
        initial=26,
        min_value=3,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    macd_signal = forms.IntegerField(
        initial=9,
        min_value=2,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    initial_balance = forms.DecimalField(
        initial=100000,
        min_value=1,
        decimal_places=2,
        max_digits=18,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input", "step": "0.01"}),
    )
    allocation_fraction = forms.FloatField(
        initial=1.0,
        min_value=0.01,
        max_value=1.0,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input", "step": "0.05"}),
    )
    simulations = forms.IntegerField(
        initial=150,
        min_value=100,
        max_value=200,
        widget=forms.NumberInput(attrs={"class": "form-control kinetic-input"}),
    )
    symbol = forms.CharField(
        initial="BTC/USDT",
        max_length=64,
        widget=forms.TextInput(
            attrs={"class": "form-control kinetic-input", "placeholder": "Symbol / instrument"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        strategy = cleaned_data.get("strategy")
        short_window = cleaned_data.get("short_window")
        long_window = cleaned_data.get("long_window")
        macd_fast = cleaned_data.get("macd_fast")
        macd_slow = cleaned_data.get("macd_slow")
        rsi_oversold = cleaned_data.get("rsi_oversold")
        rsi_overbought = cleaned_data.get("rsi_overbought")

        if strategy == "ma_crossover" and short_window and long_window and short_window >= long_window:
            raise forms.ValidationError("Short window must be lower than the long window.")

        if macd_fast and macd_slow and macd_fast >= macd_slow:
            raise forms.ValidationError("MACD fast period must be lower than the slow period.")

        if rsi_oversold and rsi_overbought and rsi_oversold >= rsi_overbought:
            raise forms.ValidationError("RSI oversold level must be below the overbought level.")

        return cleaned_data
