from __future__ import annotations

from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard_page, name="dashboard"),
    path("upload-page/", views.upload_page, name="upload_page"),
    path("results-page/", views.results_page, name="results_page"),
    path("upload/", views.upload_dataset_api, name="upload_dataset_api"),
    path("run-backtest/", views.run_backtest, name="run_backtest"),
    path("run-backtest-api/", views.run_backtest_api, name="run_backtest_api"),
    path("backtest/", views.backtest_api, name="backtest_api"),
    path("results/", views.results_api, name="results_api"),
    path("download-trades/", views.download_trades, name="download_trades"),
]
