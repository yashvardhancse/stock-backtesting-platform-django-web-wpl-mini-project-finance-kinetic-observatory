# Kinetic Observatory

A web-based stock backtesting and visualization platform built for a WPL mini project, with a TradingView-inspired terminal UI and a Django backend.

## Features

- CSV upload with form validation and media storage
- OHLCV cleaning and chronological sorting
- Strategy engine for SMA/EMA crossover, RSI, VWAP, Bollinger Bands, and MACD
- Moving-average, RSI, VWAP, Bollinger, and MACD indicator overlays
- Backtesting, equity curve generation, trade logging, and risk metrics
- Monte Carlo simulation using bootstrapped daily returns
- Paper trading with an initial balance of ₹100,000
- AJAX + JSON endpoints for upload, data, backtest, and results
- Bootstrap 5, jQuery, and Chart.js driven UI

## Tech Stack

- Django 6
- SQLite
- Pandas
- NumPy
- HTML5, CSS3, Bootstrap 5
- JavaScript, jQuery, Chart.js

## Project Layout

```text
backend/core/        Django project and trading app
data/                Data and generated outputs
docs/                Documentation
google stitch exports/  Design prototype assets
```

## Run Locally

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd backend\core
python manage.py makemigrations
python manage.py migrate
python manage.py test trading
python manage.py runserver
```

Open the app at:

```text
http://127.0.0.1:8000/
```

## API Endpoints

- `/upload/` - CSV upload and validation
- `/data/` - OHLCV data table payload
- `/backtest/` - Strategy execution and analytics
- `/results/` - Latest or selected backtest result

## Testing Scope

- File type validation
- Missing OHLCV column validation
- Indicator and strategy execution
- Monte Carlo output shape
- End-to-end upload/backtest/results flow

## Notes

- The `frontend/`, `infra/`, `ml/`, and `scripts/` folders were removed to keep the project aligned with the requested syllabus structure.
- Design prototype assets remain in `google stitch exports/`.

Use GitHub Issues for:

* Feature development
* Bug tracking
* Task assignment

### Suggested Initial Issues:

* Setup Django Project
* CSV Upload API
* OHLCV Parser
* Backtesting Engine (Basic)
* UI for Data Display
* Telegram Webhook Integration
* Paper Trading Module

---

## ⚠️ Important Notes

* Do NOT upload large datasets to GitHub
* Keep `data/` folder lightweight
* Use `.env` for secrets (API keys, tokens)
* Follow clean code practices

---

## 🔮 Future Enhancements

* Machine Learning predictions
* Real-time stock data APIs
* Strategy building & optimization
* React + FastAPI migration (advanced version)
* Cloud deployment (AWS/GCP)
---

## 📄 License

This project is developed for academic and learning purposes.
