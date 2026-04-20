from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import BacktestConfigForm, DatasetUploadForm
from .models import BacktestResult, Trade, UploadedDataset
from .services import BacktestConfig, dataframe_records, handle_upload, run_backtest as run_backtest_service


MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _json_safe(value):
	if isinstance(value, Decimal):
		return float(value)
	if isinstance(value, dict):
		return {key: _json_safe(item) for key, item in value.items()}
	if isinstance(value, list):
		return [_json_safe(item) for item in value]
	return value


def _make_aware_datetime(value):
	timestamp = pd.to_datetime(value).to_pydatetime()
	if timezone.is_naive(timestamp):
		return timezone.make_aware(timestamp, MARKET_TIMEZONE)
	return timestamp


def _format_market_datetime(value) -> str:
	timestamp = value
	if hasattr(timestamp, "to_pydatetime"):
		timestamp = timestamp.to_pydatetime()
	if timezone.is_naive(timestamp):
		timestamp = timezone.make_aware(timestamp, MARKET_TIMEZONE)
	return timezone.localtime(timestamp, MARKET_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def _dataset_payload(dataset: UploadedDataset) -> dict:
	return {
		"id": dataset.id,
		"original_name": dataset.original_name,
		"row_count": dataset.row_count,
		"uploaded_at": _format_market_datetime(dataset.uploaded_at),
		"file": dataset.file.url if dataset.file else None,
		"columns": dataset.column_snapshot,
	}


def _trade_payload(trade: Trade) -> dict:
	entry_price = float(trade.entry_price)
	quantity = int(trade.quantity or 1)
	capital_allocated = entry_price * quantity

	return {
		"id": trade.id,
		"entry_time": _format_market_datetime(trade.entry_date),
		"exit_time": _format_market_datetime(trade.exit_date),
		"buy_price": entry_price,
		"sell_price": float(trade.exit_price),
		"quantity": quantity,
		"capital_allocated": round(capital_allocated, 2),
		"profit": float(trade.profit),
		"created_at": _format_market_datetime(trade.created_at),
	}


def _error_response(message: str, *, status: int = 400):
	return JsonResponse({"success": False, "error": message, "message": message}, status=status)


def _first_form_error(form) -> str:
	for errors in form.errors.get_json_data().values():
		if errors:
			return errors[0].get("message", "Validation failed.")
	return "Validation failed."


def _empty_summary() -> dict:
	return {
		"initial_balance": 100000.0,
		"total_profit": 0.0,
		"num_trades": 0,
		"win_percent": 0.0,
	}


def _latest_dataset() -> UploadedDataset | None:
	return UploadedDataset.objects.order_by("-uploaded_at", "-id").first()


def _latest_result() -> BacktestResult | None:
	return (
		BacktestResult.objects.select_related("dataset")
		.prefetch_related("trades")
		.order_by("-created_at", "-id")
		.first()
	)


def _resolve_dataset(request, dataset_id: str | None) -> UploadedDataset | None:
	if dataset_id:
		return get_object_or_404(UploadedDataset, pk=dataset_id)

	session_dataset_id = request.session.get("latest_dataset_id")
	if session_dataset_id:
		session_dataset = UploadedDataset.objects.filter(pk=session_dataset_id).first()
		if session_dataset is not None:
			return session_dataset

	return _latest_dataset()


def _page_context(request, page_slug: str, *, include_summary: bool = True) -> dict:
	latest_dataset = _resolve_dataset(request, None)

	latest_result = None
	if include_summary:
		session_result_id = request.session.get("latest_result_id")
		if session_result_id:
			latest_result = (
				BacktestResult.objects.select_related("dataset")
				.prefetch_related("trades")
				.filter(pk=session_result_id)
				.first()
			)
		if latest_result is None:
			latest_result = _latest_result()

	summary = (
		{
			"initial_balance": float((latest_result.metrics or {}).get("initial_balance", 100000.0)),
			"total_profit": float(latest_result.profit),
			"num_trades": int(latest_result.trade_count),
			"win_percent": float((latest_result.metrics or {}).get("win_percent", 0.0)),
		}
		if latest_result
		else _empty_summary()
	)
	return {
		"page_slug": page_slug,
		"upload_form": DatasetUploadForm(),
		"strategy_form": BacktestConfigForm(),
		"datasets": UploadedDataset.objects.order_by("-uploaded_at", "-id")[:20],
		"latest_dataset_id": latest_dataset.id if latest_dataset else None,
		"latest_result_id": latest_result.id if latest_result else None,
		"summary": summary,
		"recent_results": BacktestResult.objects.select_related("dataset").order_by("-created_at", "-id")[:8],
		"page_title": "Kinetic Observatory",
	}


def dashboard_page(request):
	context = _page_context(request, "dashboard")
	return render(request, "trading/dashboard.html", context)


def upload_page(request):
	context = _page_context(request, "upload", include_summary=False)
	return render(request, "trading/upload.html", context)


def results_page(request):
	context = _page_context(request, "results")
	return render(request, "trading/results.html", context)


@require_POST
def upload_dataset_api(request):
	uploaded_file = request.FILES.get("dataset_file") or request.FILES.get("file")
	if not uploaded_file:
		return _error_response("No file uploaded", status=400)

	dataset_name = (request.POST.get("label") or uploaded_file.name).strip() or uploaded_file.name
	upload_result = handle_upload(uploaded_file)
	if "error" in upload_result:
		return _error_response(upload_result["error"], status=400)

	cleaned_frame = upload_result["cleaned_frame"]
	dataset = UploadedDataset.objects.create(
		file=uploaded_file,
		original_name=dataset_name,
		row_count=int(len(cleaned_frame)),
		column_snapshot=list(cleaned_frame.columns),
	)
	request.session["latest_dataset_id"] = dataset.id
	request.session["latest_dataset_path"] = dataset.file.name if dataset.file else ""
	request.session["latest_csv_path"] = upload_result.get("latest_csv_path", "")

	preview_rows = dataframe_records(cleaned_frame.head(10))
	response_payload = {
		"success": True,
		"message": "Upload successful",
		"dataset": _dataset_payload(dataset),
		"preview_rows": preview_rows,
		"preview_count": len(preview_rows),
	}
	return JsonResponse(response_payload, status=201)


@require_POST
def run_backtest(request):
	print("BACKTEST HIT")
	return _run_backtest_impl(request)


@require_POST
def run_backtest_api(request):
	return _run_backtest_impl(request)


def _run_backtest_impl(request):
	form = BacktestConfigForm(request.POST)
	if not form.is_valid():
		error_message = _first_form_error(form)
		return JsonResponse(
			{"success": False, "error": error_message, "errors": form.errors.get_json_data()},
			status=400,
		)

	dataset = _resolve_dataset(request, request.POST.get("dataset_id"))
	if dataset is None:
		return _error_response("Upload a dataset before running a backtest.", status=404)

	latest_csv_path = request.session.get("latest_csv_path")
	if latest_csv_path:
		csv_path = Path(latest_csv_path)
	else:
		csv_path = Path(settings.MEDIA_ROOT) / "latest.csv"

	if not csv_path.exists():
		return _error_response("Upload Excel before running backtest.", status=400)

	try:
		frame = pd.read_csv(csv_path)
		frame.columns = [str(column).strip().capitalize() for column in frame.columns]
		required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
		for column in required_columns:
			if column not in frame.columns:
				return _error_response(f"Missing column: {column}", status=400)

		frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
		for column in ["Open", "High", "Low", "Close", "Volume"]:
			frame[column] = pd.to_numeric(frame[column], errors="coerce")
		frame = frame.dropna(subset=required_columns).sort_values("Date").reset_index(drop=True)
	except Exception as exc:
		return _error_response(str(exc), status=400)

	if frame.empty:
		return _error_response("Dataset is empty after cleaning.", status=400)

	cleaned_data = form.cleaned_data
	config = BacktestConfig(
		strategy=cleaned_data["strategy"],
		short_window=cleaned_data.get("short_window") or 9,
		long_window=cleaned_data.get("long_window") or 21,
		rsi_period=cleaned_data.get("rsi_period") or 14,
		ema_window=cleaned_data.get("ema_window") or 20,
		initial_balance=100000.0,
		symbol=(dataset.original_name or "NSE")[:64],
	)

	run_payload = run_backtest_service(frame, config)
	initial_balance = float(run_payload.get("initial_balance", config.initial_balance))
	total_profit = float(run_payload["total_profit"])
	num_trades = int(run_payload["num_trades"])
	win_percent = float(run_payload.get("win_percent", 0.0))
	trade_rows = run_payload["trades"]
	metrics = {
		"initial_balance": initial_balance,
		"total_profit": total_profit,
		"num_trades": num_trades,
		"win_percent": win_percent,
		"strategy": config.strategy,
	}

	with transaction.atomic():
		backtest_result = BacktestResult.objects.create(
			dataset=dataset,
			symbol=config.symbol,
			strategy_name=config.strategy,
			parameters=_json_safe(cleaned_data),
			profit=Decimal(str(total_profit)),
			trade_count=num_trades,
			metrics=metrics,
			price_payload=[],
			indicator_payload={},
			signal_payload=[],
			equity_curve=[],
			monte_carlo_payload={},
			paper_trading_payload={},
		)

		trade_instances = []
		for trade_row in trade_rows:
			buy_price = float(trade_row["buy_price"])
			sell_price = float(trade_row["sell_price"])
			quantity = max(int(trade_row.get("quantity") or 1), 1)
			profit = float(trade_row["profit"])
			invested_amount = buy_price * quantity
			profit_pct = (profit / invested_amount * 100.0) if invested_amount else 0.0
			trade_instances.append(
				Trade(
					backtest_result=backtest_result,
					symbol=config.symbol,
					side=Trade.LONG,
					entry_date=_make_aware_datetime(trade_row["entry_time"]),
					exit_date=_make_aware_datetime(trade_row["exit_time"]),
					entry_price=Decimal(str(buy_price)),
					exit_price=Decimal(str(sell_price)),
					quantity=quantity,
					profit=Decimal(str(profit)),
					profit_pct=Decimal(str(round(profit_pct, 4))),
					exit_reason="signal",
				)
			)
		if trade_instances:
			Trade.objects.bulk_create(trade_instances)

	response_payload = {
		"success": True,
		"message": "Backtest completed successfully",
		"result_id": backtest_result.id,
		"initial_balance": initial_balance,
		"total_profit": total_profit,
		"num_trades": num_trades,
		"win_percent": win_percent,
		"trades": trade_rows,
		"dataset": _dataset_payload(dataset),
		"strategy": config.strategy,
	}
	request.session["trades"] = trade_rows
	request.session["latest_result_id"] = backtest_result.id
	request.session["latest_dataset_id"] = dataset.id
	return JsonResponse(response_payload)


# Backward-compatible alias for older route naming.
backtest_api = run_backtest


@require_GET
def results_api(request):
	result_id = request.GET.get("result_id")
	if result_id:
		result = get_object_or_404(BacktestResult, pk=result_id)
	else:
		session_result_id = request.session.get("latest_result_id")
		result = None
		if session_result_id:
			result = (
				BacktestResult.objects.select_related("dataset")
				.prefetch_related("trades")
				.filter(pk=session_result_id)
				.first()
			)
		if result is None:
			result = _latest_result()
	if result is None:
		return _error_response("No backtest results available.", status=404)

	trades = [_trade_payload(trade) for trade in result.trades.order_by("entry_date", "id")]
	metrics = result.metrics or {}
	return JsonResponse(
		{
			"success": True,
			"result_id": result.id,
			"strategy": result.strategy_name,
			"dataset": _dataset_payload(result.dataset),
			"initial_balance": float(metrics.get("initial_balance", 100000.0)),
			"total_profit": float(result.profit),
			"num_trades": int(result.trade_count),
			"win_percent": float(metrics.get("win_percent", 0.0)),
			"trades": trades,
		}
	)


@require_GET
def download_trades(request):
	result_id = request.GET.get("result_id")

	trade_rows = []
	if result_id:
		result = get_object_or_404(BacktestResult, pk=result_id)
		trade_rows = [
			{
				"quantity": int(trade.quantity or 1),
				"capital_allocated": round(float(trade.entry_price) * int(trade.quantity or 1), 2),
				"entry_time": _format_market_datetime(trade.entry_date),
				"exit_time": _format_market_datetime(trade.exit_date),
				"buy_price": float(trade.entry_price),
				"sell_price": float(trade.exit_price),
				"profit": float(trade.profit),
			}
			for trade in result.trades.order_by("entry_date", "id")
		]
	else:
		trade_rows = request.session.get("trades", [])
		if not trade_rows:
			result = _latest_result()
			if result is not None:
				trade_rows = [
					{
						"quantity": int(trade.quantity or 1),
						"capital_allocated": round(float(trade.entry_price) * int(trade.quantity or 1), 2),
						"entry_time": _format_market_datetime(trade.entry_date),
						"exit_time": _format_market_datetime(trade.exit_date),
						"buy_price": float(trade.entry_price),
						"sell_price": float(trade.exit_price),
						"profit": float(trade.profit),
					}
					for trade in result.trades.order_by("entry_date", "id")
				]

	if not trade_rows:
		return _error_response("No trade log available. Run a backtest first.", status=404)

	response = HttpResponse(content_type="text/csv")
	response["Content-Disposition"] = 'attachment; filename="trades.csv"'

	writer = csv.writer(response)
	writer.writerow(["Entry Time", "Exit Time", "Buy Price", "Sell Price", "Quantity", "Capital Allocated", "Profit"])

	for trade in trade_rows:
		writer.writerow(
			[
				trade.get("entry_time", ""),
				trade.get("exit_time", ""),
				trade.get("buy_price", 0),
				trade.get("sell_price", 0),
				trade.get("quantity", 1),
				trade.get("capital_allocated", trade.get("capital_used", 0)),
				trade.get("profit", 0),
			]
		)

	return response
