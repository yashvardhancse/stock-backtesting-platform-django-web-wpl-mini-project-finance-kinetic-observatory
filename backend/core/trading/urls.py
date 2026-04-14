from __future__ import annotations

from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard_page, name="dashboard"),
    path("upload-page/", views.upload_page, name="upload_page"),
    path("data-page/", views.data_page, name="data_page"),
    path("results-page/", views.results_page, name="results_page"),
    path("upload/", views.upload_dataset_api, name="upload_dataset_api"),
    path("data/", views.data_api, name="data_api"),
    path("backtest/", views.backtest_api, name="backtest_api"),
    path("results/", views.results_api, name="results_api"),
]
