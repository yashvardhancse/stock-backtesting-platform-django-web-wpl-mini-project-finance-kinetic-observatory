from django.contrib import admin
from .models import UploadedDataset, BacktestResult, Trade, Portfolio


@admin.register(UploadedDataset)
class UploadedDatasetAdmin(admin.ModelAdmin):
    list_display = ["original_name", "row_count", "uploaded_at"]
    list_filter = ["uploaded_at"]
    search_fields = ["original_name"]
    readonly_fields = ["uploaded_at", "column_snapshot", "file"]


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ["strategy_name", "symbol", "profit", "trade_count", "created_at"]
    list_filter = ["strategy_name", "created_at"]
    search_fields = ["symbol", "strategy_name"]
    readonly_fields = [
        "created_at",
        "parameters",
        "metrics",
    ]
    fieldsets = (
        ("Strategy", {"fields": ("dataset", "symbol", "strategy_name", "parameters")}),
        ("Results", {"fields": ("profit", "trade_count", "metrics")}),
        ("Metadata", {"fields": ("created_at",)}),
    )


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ["symbol", "side", "entry_date", "exit_date", "profit", "profit_pct"]
    list_filter = ["side", "entry_date"]
    search_fields = ["symbol"]
    readonly_fields = ["created_at"]
    fieldsets = (
        (
            "Trade Info",
            {"fields": ("backtest_result", "symbol", "side", "quantity", "exit_reason")},
        ),
        (
            "Entry",
            {"fields": ("entry_date", "entry_price")},
        ),
        (
            "Exit",
            {"fields": ("exit_date", "exit_price")},
        ),
        (
            "P&L",
            {"fields": ("profit", "profit_pct")},
        ),
        ("Metadata", {"fields": ("created_at",)}),
    )


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["name", "initial_balance", "balance", "realized_pnl", "is_active"]
    list_filter = ["is_active", "updated_at"]
    readonly_fields = ["updated_at", "positions", "equity_curve"]
    fieldsets = (
        ("Portfolio Info", {"fields": ("name", "backtest_result", "is_active")}),
        (
            "Balance",
            {"fields": ("initial_balance", "balance", "realized_pnl")},
        ),
        (
            "Data",
            {"fields": ("positions", "equity_curve")},
        ),
        ("Metadata", {"fields": ("updated_at",)}),
    )
