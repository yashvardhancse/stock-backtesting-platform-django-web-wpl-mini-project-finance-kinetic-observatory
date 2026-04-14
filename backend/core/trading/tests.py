from __future__ import annotations

from io import BytesIO

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from .forms import BacktestConfigForm
from .services import BacktestConfig, load_clean_dataset, run_backtest, run_monte_carlo_simulation, validate_uploaded_csv


class DatasetServiceTests(SimpleTestCase):
	def test_validate_uploaded_csv_rejects_missing_columns(self):
		csv_bytes = b"Date,Open,High,Low,Close\n2024-01-01,10,11,9,10\n"
		uploaded_file = SimpleUploadedFile("sample.csv", csv_bytes, content_type="text/csv")

		result = validate_uploaded_csv(uploaded_file)

		self.assertFalse(result.is_valid)
		self.assertTrue(any("Volume" in error for error in result.errors))

	def test_validate_uploaded_csv_accepts_excel_files(self):
		frame = pd.DataFrame(
			{
				"Date": ["2024-01-01", "2024-01-02"],
				"Open": [10, 11],
				"High": [11, 12],
				"Low": [9, 10],
				"Close": [10, 11],
				"Volume": [100, 200],
			}
		)
		buffer = BytesIO()
		frame.to_excel(buffer, index=False)
		uploaded_file = SimpleUploadedFile(
			"sample.xlsx",
			buffer.getvalue(),
			content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		)

		result = validate_uploaded_csv(uploaded_file)

		self.assertTrue(result.is_valid)

	def test_load_clean_dataset_sorts_and_coerces_data(self):
		csv_bytes = b"Date,Open,High,Low,Close,Volume\n2024-01-03,12,13,11,12,300\n2024-01-01,10,11,9,10,100\n2024-01-02,11,12,10,11,200\n"
		uploaded_file = SimpleUploadedFile("sorted.csv", csv_bytes, content_type="text/csv")

		frame = load_clean_dataset(uploaded_file)

		self.assertEqual(list(frame["Date"].dt.strftime("%Y-%m-%d")), ["2024-01-01", "2024-01-02", "2024-01-03"])
		self.assertEqual(frame.iloc[0]["Close"], 10)
		self.assertIn("Returns", frame.columns)


class StrategyEngineTests(SimpleTestCase):
	def _sample_frame(self):
		return pd.DataFrame(
			{
				"Date": pd.date_range("2024-01-01", periods=9, freq="D"),
				"Open": [10, 9, 8, 7, 8, 9, 12, 13, 14],
				"High": [11, 10, 9, 8, 9, 10, 13, 14, 15],
				"Low": [9, 8, 7, 6, 7, 8, 11, 12, 13],
				"Close": [10, 9, 8, 7, 8, 9, 12, 13, 14],
				"Volume": [100, 120, 140, 160, 180, 200, 220, 240, 260],
			}
		)

	def test_ma_crossover_generates_trade_rows(self):
		config = BacktestConfig(
			strategy="ma_crossover",
			ma_type="sma",
			short_window=2,
			long_window=3,
			simulations=120,
			symbol="TEST",
		)

		result = run_backtest(self._sample_frame(), config)

		self.assertGreaterEqual(result["metrics"]["trade_count"], 1)
		self.assertTrue(result["trade_rows"])
		self.assertIn("price_payload", result)
		self.assertIn("monte_carlo_payload", result)

	def test_monte_carlo_distribution_has_expected_shape(self):
		monte_carlo = run_monte_carlo_simulation(pd.Series([0.01, -0.02, 0.03, 0.015]), simulations=150)

		self.assertEqual(len(monte_carlo["final_values"]), 150)
		self.assertEqual(sum(monte_carlo["histogram"]["counts"]), 150)
		self.assertIn("mean", monte_carlo)
		self.assertIn("variance", monte_carlo)


class FormValidationTests(SimpleTestCase):
	def test_backtest_config_form_rejects_invalid_windows(self):
		form = BacktestConfigForm(
			data={
				"strategy": "ma_crossover",
				"ma_type": "sma",
				"short_window": 20,
				"long_window": 10,
				"rsi_period": 14,
				"rsi_oversold": 30,
				"rsi_overbought": 70,
				"bb_window": 20,
				"bb_std_dev": 2.0,
				"macd_fast": 12,
				"macd_slow": 26,
				"macd_signal": 9,
				"initial_balance": 100000,
				"allocation_fraction": 1.0,
				"simulations": 150,
				"symbol": "TEST",
			}
		)

		self.assertFalse(form.is_valid())
		self.assertIn("Short window must be lower than the long window.", form.non_field_errors())


class ApiIntegrationTests(TestCase):
	def test_upload_backtest_and_results_flow(self):
		csv_bytes = (
			b"Date,Open,High,Low,Close,Volume\n"
			b"2024-01-01,10,11,9,10,100\n"
			b"2024-01-02,9,10,8,9,120\n"
			b"2024-01-03,8,9,7,8,140\n"
			b"2024-01-04,7,8,6,7,160\n"
			b"2024-01-05,8,9,7,8,180\n"
			b"2024-01-06,9,10,8,9,200\n"
			b"2024-01-07,12,13,11,12,220\n"
			b"2024-01-08,13,14,12,13,240\n"
			b"2024-01-09,14,15,13,14,260\n"
		)
		uploaded_file = SimpleUploadedFile("sample.csv", csv_bytes, content_type="text/csv")

		upload_response = self.client.post(
			"/upload/",
			data={"csv_file": uploaded_file, "label": "Integration Dataset"},
		)

		self.assertEqual(upload_response.status_code, 201)
		upload_payload = upload_response.json()
		dataset_id = upload_payload["dataset"]["id"]

		backtest_response = self.client.post(
			"/backtest/",
			data={
				"dataset_id": dataset_id,
				"strategy": "ma_crossover",
				"ma_type": "sma",
				"short_window": 2,
				"long_window": 3,
				"rsi_period": 14,
				"rsi_oversold": 30,
				"rsi_overbought": 70,
				"bb_window": 3,
				"bb_std_dev": 2.0,
				"macd_fast": 12,
				"macd_slow": 26,
				"macd_signal": 9,
				"initial_balance": 100000,
				"allocation_fraction": 1.0,
				"simulations": 120,
				"symbol": "TEST",
			},
		)

		self.assertEqual(backtest_response.status_code, 201)
		backtest_payload = backtest_response.json()
		self.assertTrue(backtest_payload["success"])
		self.assertGreaterEqual(backtest_payload["metrics"]["trade_count"], 1)

		results_response = self.client.get(f"/results/?result_id={backtest_payload['result_id']}")
		self.assertEqual(results_response.status_code, 200)
		results_payload = results_response.json()
		self.assertEqual(results_payload["result"]["id"], backtest_payload["result_id"])

		data_response = self.client.get(f"/data/?dataset_id={dataset_id}")
		self.assertEqual(data_response.status_code, 200)
		self.assertGreaterEqual(len(data_response.json()["rows"]), 1)
