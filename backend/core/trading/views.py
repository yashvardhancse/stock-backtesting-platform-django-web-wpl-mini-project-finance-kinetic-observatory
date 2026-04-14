from __future__ import annotations

from decimal import Decimal

import pandas as pd
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import BacktestConfigForm, DatasetUploadForm
from .models import BacktestResult, Portfolio, Trade, UploadedDataset
from .services import BacktestConfig, dataframe_records, load_clean_dataset, run_backtest, validate_uploaded_csv


PAGE_SIZE_DEFAULT = 100
PAGE_SIZE_MAX = 500


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
		return timezone.make_aware(timestamp)
	return timestamp


def _dataset_payload(dataset: UploadedDataset) -> dict:
	return {
		"id": dataset.id,
		"original_name": dataset.original_name,
		"row_count": dataset.row_count,
		"uploaded_at": dataset.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
		"file": dataset.file.url if dataset.file else None,
		"columns": dataset.column_snapshot,
	}


def _trade_payload(trade: Trade) -> dict:
	return {
		"id": trade.id,
		"symbol": trade.symbol,
		"side": trade.side,
		"entry_date": trade.entry_date.strftime("%Y-%m-%d %H:%M:%S"),
		"exit_date": trade.exit_date.strftime("%Y-%m-%d %H:%M:%S"),
		"entry_price": float(trade.entry_price),
		"exit_price": float(trade.exit_price),
		"quantity": trade.quantity,
		"profit": float(trade.profit),
		"profit_pct": float(trade.profit_pct),
		"exit_reason": trade.exit_reason,
	}


def _portfolio_payload(portfolio: Portfolio | None) -> dict:
	if portfolio is None:
		return {}
	return {
		"id": portfolio.id,
		"name": portfolio.name,
		"initial_balance": float(portfolio.initial_balance),
		"balance": float(portfolio.balance),
		"realized_pnl": float(portfolio.realized_pnl),
		"positions": portfolio.positions,
		"equity_curve": portfolio.equity_curve,
		"is_active": portfolio.is_active,
		"updated_at": portfolio.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
	}


def _result_payload(result: BacktestResult) -> dict:
	trades = [_trade_payload(trade) for trade in result.trades.all()]
	try:
		portfolio = result.portfolio
	except Portfolio.DoesNotExist:
		portfolio = None
	return {
		"id": result.id,
		"dataset": _dataset_payload(result.dataset),
		"symbol": result.symbol,
		"strategy_name": result.strategy_name,
		"parameters": result.parameters,
		"profit": float(result.profit),
		"trade_count": result.trade_count,
		"metrics": result.metrics,
		"price_data": result.price_payload,
		"indicators": result.indicator_payload,
		"signals": result.signal_payload,
		"equity_curve": result.equity_curve,
		"trades": trades,
		"monte_carlo": result.monte_carlo_payload,
		"paper_trading": result.paper_trading_payload,
		"portfolio": _portfolio_payload(portfolio),
		"created_at": result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
	}


def _empty_summary() -> dict:
	return {
		"total_profit": 0.0,
		"trade_count": 0,
		"win_rate": 0.0,
		"max_drawdown": 0.0,
		"sharpe_ratio": 0.0,
		"total_return_pct": 0.0,
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


def _page_context(page_slug: str, *, include_summary: bool = True) -> dict:
	latest_dataset = _latest_dataset()
	latest_result = _latest_result() if include_summary else None
	summary = latest_result.metrics if latest_result else _empty_summary()
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


def _load_dataset_frame(dataset: UploadedDataset) -> pd.DataFrame:
	return load_clean_dataset(dataset.file)


def dashboard_page(request):
	context = _page_context("dashboard")
	return render(request, "trading/dashboard.html", context)


def upload_page(request):
	context = _page_context("upload", include_summary=False)
	return render(request, "trading/upload.html", context)


def data_page(request):
	context = _page_context("data", include_summary=False)
	return render(request, "trading/data.html", context)


def results_page(request):
	context = _page_context("results")
	return render(request, "trading/results.html", context)


@require_POST
def upload_dataset_api(request):
	form = DatasetUploadForm(request.POST, request.FILES)
	if not form.is_valid():
		return JsonResponse({"success": False, "message": "Upload validation failed.", "errors": form.errors}, status=400)

	uploaded_file = form.cleaned_data["csv_file"]
	validation_result = validate_uploaded_csv(uploaded_file)
	if not validation_result.is_valid:
		return JsonResponse(
			{"success": False, "message": "Dataset validation failed.", "errors": validation_result.errors},
			status=400,
		)

	try:
		cleaned_frame = load_clean_dataset(uploaded_file)
	except Exception as exc:
		return JsonResponse({"success": False, "message": str(exc)}, status=400)

	dataset_name = form.cleaned_data.get("label") or uploaded_file.name
	dataset = UploadedDataset.objects.create(
		file=uploaded_file,
		original_name=dataset_name,
		row_count=int(len(cleaned_frame)),
		column_snapshot=list(cleaned_frame.columns),
	)

	preview_rows = dataframe_records(cleaned_frame.head(10))
	response_payload = {
		"success": True,
		"message": "Dataset uploaded successfully.",
		"dataset": _dataset_payload(dataset),
		"preview_rows": preview_rows,
		"preview_count": len(preview_rows),
	}
	return JsonResponse(response_payload, status=201)


@require_GET
def data_api(request):
	dataset_id = request.GET.get("dataset_id")
	dataset = get_object_or_404(UploadedDataset, pk=dataset_id) if dataset_id else _latest_dataset()
	if dataset is None:
		return JsonResponse({"success": False, "message": "No uploaded datasets available."}, status=404)

	try:
		frame = _load_dataset_frame(dataset)
	except Exception as exc:
		return JsonResponse({"success": False, "message": str(exc)}, status=400)

	search_text = (request.GET.get("search") or "").strip().lower()
	if search_text:
		searchable_frame = frame.astype(str)
		search_mask = searchable_frame.apply(lambda column: column.str.contains(search_text, case=False, na=False))
		frame = frame.loc[search_mask.any(axis=1)]

	sort_by = request.GET.get("sort_by") or "Date"
	sort_dir = request.GET.get("sort_dir") or "asc"
	if sort_by in frame.columns:
		frame = frame.sort_values(sort_by, ascending=sort_dir != "desc")

	try:
		page_size = min(max(int(request.GET.get("page_size", PAGE_SIZE_DEFAULT)), 1), PAGE_SIZE_MAX)
	except (TypeError, ValueError):
		page_size = PAGE_SIZE_DEFAULT
	try:
		page = max(int(request.GET.get("page", 1)), 1)
	except (TypeError, ValueError):
		page = 1
	start = (page - 1) * page_size
	end = start + page_size
	page_frame = frame.iloc[start:end].copy()

	response_payload = {
		"success": True,
		"dataset": _dataset_payload(dataset),
		"columns": ["Date", "Open", "High", "Low", "Close", "Volume"],
		"rows": dataframe_records(page_frame[["Date", "Open", "High", "Low", "Close", "Volume"]]),
		"total_rows": int(len(frame)),
		"page": page,
		"page_size": page_size,
		"sort_by": sort_by,
		"sort_dir": sort_dir,
	}
	return JsonResponse(response_payload)


@require_POST
def backtest_api(request):
	form = BacktestConfigForm(request.POST)
	if not form.is_valid():
		return JsonResponse({"success": False, "message": "Backtest validation failed.", "errors": form.errors}, status=400)

	dataset_id = request.POST.get("dataset_id")
	dataset = get_object_or_404(UploadedDataset, pk=dataset_id) if dataset_id else _latest_dataset()
	if dataset is None:
		return JsonResponse({"success": False, "message": "Upload a dataset before running a backtest."}, status=404)

	try:
		frame = _load_dataset_frame(dataset)
	except Exception as exc:
		return JsonResponse({"success": False, "message": str(exc)}, status=400)

	cleaned_data = form.cleaned_data
	config = BacktestConfig(
		strategy=cleaned_data["strategy"],
		ma_type=cleaned_data["ma_type"],
		short_window=cleaned_data["short_window"],
		long_window=cleaned_data["long_window"],
		rsi_period=cleaned_data["rsi_period"],
		rsi_oversold=cleaned_data["rsi_oversold"],
		rsi_overbought=cleaned_data["rsi_overbought"],
		bb_window=cleaned_data["bb_window"],
		bb_std_dev=cleaned_data["bb_std_dev"],
		macd_fast=cleaned_data["macd_fast"],
		macd_slow=cleaned_data["macd_slow"],
		macd_signal=cleaned_data["macd_signal"],
		initial_balance=float(cleaned_data["initial_balance"]),
		allocation_fraction=float(cleaned_data["allocation_fraction"]),
		simulations=cleaned_data["simulations"],
		symbol=cleaned_data["symbol"],
	)

	run_payload = run_backtest(frame, config)
	metrics = run_payload["metrics"]

	with transaction.atomic():
		backtest_result = BacktestResult.objects.create(
			dataset=dataset,
			symbol=config.symbol,
			strategy_name=config.strategy,
			parameters=_json_safe(cleaned_data),
			profit=Decimal(str(metrics["total_profit"])),
			trade_count=len(run_payload["trade_rows"]),
			metrics=metrics,
			price_payload=run_payload["price_payload"],
			indicator_payload=run_payload["indicator_payload"],
			signal_payload=run_payload["signal_payload"],
			equity_curve=run_payload["equity_rows"],
			monte_carlo_payload=run_payload["monte_carlo_payload"],
			paper_trading_payload=run_payload["paper_trading_payload"],
		)

		trade_instances = []
		for trade_row in run_payload["trade_rows"]:
			trade_instances.append(
				Trade(
					backtest_result=backtest_result,
					symbol=trade_row["symbol"],
					side=Trade.LONG,
					entry_date=_make_aware_datetime(trade_row["entry_date"]),
					exit_date=_make_aware_datetime(trade_row["exit_date"]),
					entry_price=Decimal(str(trade_row["entry_price"])),
					exit_price=Decimal(str(trade_row["exit_price"])),
					quantity=trade_row["quantity"],
					profit=Decimal(str(trade_row["profit"])),
					profit_pct=Decimal(str(trade_row["profit_pct"])),
					exit_reason=trade_row["exit_reason"],
				)
			)
		Trade.objects.bulk_create(trade_instances)

		portfolio_state = run_payload["paper_trading_payload"]
		Portfolio.objects.create(
			backtest_result=backtest_result,
			name=f"{config.symbol} Paper Portfolio",
			initial_balance=Decimal(str(config.initial_balance)),
			balance=Decimal(str(portfolio_state["final_balance"])),
			realized_pnl=Decimal(str(portfolio_state["realized_pnl"])),
			positions=portfolio_state["open_positions"],
			equity_curve=portfolio_state["snapshots"],
			is_active=False,
		)

	response_payload = {
		"success": True,
		"message": "Backtest completed successfully.",
		"result_id": backtest_result.id,
		"dataset": _dataset_payload(dataset),
		"price_data": run_payload["price_payload"],
		"indicators": run_payload["indicator_payload"],
		"signals": run_payload["signal_payload"],
		"trades": run_payload["trade_rows"],
		"metrics": metrics,
		"equity_curve": run_payload["equity_rows"],
		"monte_carlo": run_payload["monte_carlo_payload"],
		"paper_trading": run_payload["paper_trading_payload"],
		"summary": {
			"total_profit": metrics["total_profit"],
			"trade_count": metrics["trade_count"],
			"win_rate": metrics["win_rate"],
			"max_drawdown": metrics["max_drawdown"],
			"sharpe_ratio": metrics["sharpe_ratio"],
		},
	}
	return JsonResponse(response_payload, status=201)


@require_GET
def results_api(request):
	result_id = request.GET.get("result_id")
	result = get_object_or_404(BacktestResult, pk=result_id) if result_id else _latest_result()
	if result is None:
		return JsonResponse({"success": False, "message": "No backtest results available."}, status=404)

	detailed_payload = _result_payload(result)
	recent_results = [
		{
			"id": item.id,
			"dataset_name": item.dataset.original_name,
			"strategy_name": item.strategy_name,
			"symbol": item.symbol,
			"profit": float(item.profit),
			"trade_count": item.trade_count,
			"created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
		}
		for item in BacktestResult.objects.select_related("dataset").order_by("-created_at", "-id")[:8]
	]

	return JsonResponse(
		{
			"success": True,
			"result": detailed_payload,
			"recent_results": recent_results,
			"summary": detailed_payload["metrics"],
		}
	)
