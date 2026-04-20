from __future__ import annotations

from io import BytesIO
from tempfile import gettempdir

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from .forms import BacktestConfigForm, DatasetUploadForm
from .services import BacktestConfig, load_clean_dataset, run_backtest, validate_uploaded_dataset


def build_sample_xlsx(filename: str, frame: pd.DataFrame) -> SimpleUploadedFile:
	buffer = BytesIO()
	frame.to_excel(buffer, index=False)
	return SimpleUploadedFile(
		filename,
		buffer.getvalue(),
		content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	)


class DatasetServiceTests(SimpleTestCase):
	def test_validate_uploaded_dataset_rejects_non_xlsx_extension(self):
		uploaded_file = SimpleUploadedFile("sample.csv", b"Date,Open\n", content_type="text/csv")
		result = validate_uploaded_dataset(uploaded_file)

		self.assertFalse(result.is_valid)
		self.assertTrue(any(".xlsx" in error for error in result.errors))

	def test_validate_uploaded_dataset_rejects_missing_columns(self):
		frame = pd.DataFrame(
			{
				"Date": ["2024-01-01", "2024-01-02"],
				"Open": [10, 11],
				"High": [11, 12],
				"Low": [9, 10],
				"Close": [10, 11],
			}
		)
		uploaded_file = build_sample_xlsx("missing_volume.xlsx", frame)

		result = validate_uploaded_dataset(uploaded_file)

		self.assertFalse(result.is_valid)
		self.assertTrue(any("volume" in error for error in result.errors))

	def test_validate_uploaded_dataset_accepts_excel_files(self):
		frame = pd.DataFrame(
			{
				"timestamp": ["2024-01-01", "2024-01-02"],
				"open": [10, 11],
				"high": [11, 12],
				"low": [9, 10],
				"close": [10, 11],
				"volume": [100, 200],
			}
		)
		uploaded_file = build_sample_xlsx("sample.xlsx", frame)

		result = validate_uploaded_dataset(uploaded_file)

		self.assertTrue(result.is_valid)

	def test_load_clean_dataset_sorts_and_coerces_data(self):
		frame = pd.DataFrame(
			{
				"datetime": ["2024-01-03", "2024-01-01", "2024-01-02"],
				"open": [12, 10, 11],
				"high": [13, 11, 12],
				"low": [11, 9, 10],
				"close": [12, 10, 11],
				"volume": [300, 100, 200],
			}
		)
		uploaded_file = build_sample_xlsx("sorted.xlsx", frame)

		frame = load_clean_dataset(uploaded_file)

		self.assertEqual(list(frame["Date"].dt.strftime("%Y-%m-%d")), ["2024-01-01", "2024-01-02", "2024-01-03"])
		self.assertEqual(frame.iloc[0]["Close"], 10)
		self.assertIn("Returns", frame.columns)


class StrategyEngineTests(SimpleTestCase):
	def _sample_frame(self):
		return pd.DataFrame(
			{
				"Date": pd.date_range("2024-01-01", periods=14, freq="D"),
				"Open": [100, 98, 96, 94, 95, 97, 99, 101, 100, 98, 96, 97, 99, 101],
				"High": [101, 99, 97, 95, 96, 98, 100, 102, 101, 99, 97, 98, 100, 102],
				"Low": [99, 97, 95, 93, 94, 96, 98, 100, 99, 97, 95, 96, 98, 100],
				"Close": [100, 98, 96, 94, 95, 97, 99, 101, 100, 98, 96, 97, 99, 101],
				"Volume": [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360],
			}
		)

	def test_moving_average_generates_trade_rows(self):
		config = BacktestConfig(
			strategy="ma",
			short_window=2,
			long_window=4,
			symbol="TEST",
		)

		result = run_backtest(self._sample_frame(), config)

		self.assertIn("total_profit", result)
		self.assertIn("num_trades", result)
		self.assertIn("trades", result)
		self.assertGreaterEqual(result["num_trades"], 1)

	def test_rsi_and_ema_strategies_return_consistent_payload_shape(self):
		rsi_result = run_backtest(self._sample_frame(), BacktestConfig(strategy="rsi", rsi_period=5))
		ema_result = run_backtest(self._sample_frame(), BacktestConfig(strategy="ema", ema_window=5))

		for payload in (rsi_result, ema_result):
			self.assertIn("total_profit", payload)
			self.assertIn("num_trades", payload)
			self.assertIn("trades", payload)


class FormValidationTests(SimpleTestCase):
	def test_dataset_upload_form_rejects_csv(self):
		uploaded_file = SimpleUploadedFile("bad.csv", b"Date,Open\n", content_type="text/csv")
		form = DatasetUploadForm(data={"label": "Bad"}, files={"dataset_file": uploaded_file})

		self.assertFalse(form.is_valid())

	def test_backtest_config_form_rejects_invalid_windows(self):
		form = BacktestConfigForm(
			data={
				"strategy": "ma",
				"short_window": 20,
				"long_window": 10,
				"rsi_period": 14,
				"ema_window": 20,
			}
		)

		self.assertFalse(form.is_valid())
		self.assertIn("Short window must be lower than the long window.", form.non_field_errors())


class ApiIntegrationTests(TestCase):
	def test_upload_backtest_and_results_flow(self):
		with self.settings(MEDIA_ROOT=gettempdir()):
			dataset_frame = pd.DataFrame(
				{
					"timestamp": pd.date_range("2024-01-01", periods=14, freq="D"),
					"open": [100, 98, 96, 94, 95, 97, 99, 101, 100, 98, 96, 97, 99, 101],
					"high": [101, 99, 97, 95, 96, 98, 100, 102, 101, 99, 97, 98, 100, 102],
					"low": [99, 97, 95, 93, 94, 96, 98, 100, 99, 97, 95, 96, 98, 100],
					"close": [100, 98, 96, 94, 95, 97, 99, 101, 100, 98, 96, 97, 99, 101],
					"volume": [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360],
				}
			)
			uploaded_file = build_sample_xlsx("sample.xlsx", dataset_frame)

			upload_response = self.client.post(
				"/upload/",
				data={"dataset_file": uploaded_file, "label": "Integration Dataset"},
			)

			self.assertEqual(upload_response.status_code, 201)
			upload_payload = upload_response.json()
			dataset_id = upload_payload["dataset"]["id"]

			backtest_response = self.client.post(
				"/run-backtest/",
				data={
					"dataset_id": dataset_id,
					"strategy": "ma",
					"short_window": 2,
					"long_window": 4,
					"rsi_period": 14,
					"ema_window": 20,
				},
			)

			self.assertEqual(backtest_response.status_code, 200)
			backtest_payload = backtest_response.json()
			self.assertTrue(backtest_payload["success"])
			self.assertIn("total_profit", backtest_payload)
			self.assertIn("num_trades", backtest_payload)
			self.assertIn("trades", backtest_payload)

			results_response = self.client.get(f"/results/?result_id={backtest_payload['result_id']}")
			self.assertEqual(results_response.status_code, 200)
			results_payload = results_response.json()
			self.assertEqual(results_payload["result_id"], backtest_payload["result_id"])

			download_response = self.client.get(f"/download-trades/?result_id={backtest_payload['result_id']}")
			self.assertEqual(download_response.status_code, 200)
			self.assertIn("text/csv", download_response["Content-Type"])
			self.assertIn("Entry Time", download_response.content.decode("utf-8"))
