# Kinetic Observatory

<p align="center">
	<a href="#"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
	<a href="#"><img src="https://img.shields.io/badge/Django-5.2%2B-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"></a>
	<a href="#"><img src="https://img.shields.io/badge/Pandas-2.2%2B-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas"></a>
	<a href="#"><img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"></a>
	<a href="#"><img src="https://img.shields.io/badge/UI-Bootstrap%205-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap"></a>
	<a href="#"><img src="https://img.shields.io/badge/Frontend-jQuery%20AJAX-0769AD?style=for-the-badge&logo=jquery&logoColor=white" alt="jQuery"></a>
	<a href="#"><img src="https://img.shields.io/badge/License-Academic-informational?style=for-the-badge&color=2F855A" alt="License"></a>
</p>

<p align="center">
	A beginner-friendly stock backtesting web app with a premium terminal-style UI.<br>
	Upload OHLCV Excel data, run one strategy, and get trades + profit/loss instantly.
</p>

---

## Table of Contents

1. [What Is This Project?](#what-is-this-project)
2. [Explain Like I Am 5](#explain-like-i-am-5)
3. [Finance Concepts (Simple + Deep)](#finance-concepts-simple--deep)
4. [How This App Works Internally](#how-this-app-works-internally)
5. [Screenshots](#screenshots)
6. [Run From Scratch (Windows, macOS, Linux)](#run-from-scratch-windows-macos-linux)
7. [How To Use The App Step-by-Step](#how-to-use-the-app-step-by-step)
8. [Input File Format](#input-file-format)
9. [API Routes](#api-routes)
10. [Project Structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [Tech Stack](#tech-stack)
13. [Future Improvements](#future-improvements)

---

## What Is This Project?

Kinetic Observatory is a Django web app for **strategy backtesting**.

You can:

- Upload one Excel file (`.xlsx`) with market candles (Date/Open/High/Low/Close/Volume).
- Choose one strategy: **MA**, **RSI**, or **EMA**.
- Run a backtest with a default capital of **INR 100,000**.
- See result summary: total P/L, number of trades, win percent.
- View each trade with quantity and capital allocated.
- Download trade log as CSV.

This project is built for learning, viva/demo, and mini-project submission.

---

## Explain Like I Am 5

Imagine this app is a **time machine game**:

- You give it an old stock history file.
- You tell it a rule, like:
	- "Buy when the line goes above another line" (MA/EMA idea)
	- "Buy when the stock looks tired" (RSI idea)
- The app plays the past like a video.
- It writes down every buy/sell in a notebook.
- Then it tells you: "Did this rule make money or lose money?"

That notebook is your **trade log**.

---

## Finance Concepts (Simple + Deep)

### Backtesting

- Simple: Test your strategy on old data before risking real money.
- Deep: A deterministic simulation where signals are generated from historical OHLCV candles and converted into executed trades.

### Candle Data (OHLCV)

- **Open**: price at candle start.
- **High**: highest price in candle.
- **Low**: lowest price in candle.
- **Close**: price at candle end.
- **Volume**: traded quantity.

### Moving Average (MA)

- Simple: Average of recent prices, like smoothing noisy lines.
- In this app:
	- Buy signal: short MA > long MA
	- Sell signal: short MA < long MA

### Exponential Moving Average (EMA)

- Simple: Like MA, but gives more importance to recent prices.
- In this app:
	- Buy signal: Close > EMA
	- Sell signal: Close < EMA

### Relative Strength Index (RSI)

- Simple: A meter from 0 to 100 telling if price moved too fast.
- Common interpretation:
	- Below 30 -> oversold area
	- Above 70 -> overbought area
- In this app:
	- Buy signal: RSI < 30
	- Sell signal: RSI > 70

### Long vs Short

- **Long** means buy first, sell later.
	- Profit if sell price > buy price.
- **Short** means sell first, buy later.
	- Profit if buy-back price < sell-first price.

Important: Current implementation stores and executes **long-side trades** for the built-in strategies.

---

## How This App Works Internally

1. Upload `.xlsx` file on Upload page.
2. File is validated and cleaned (required columns checked, sorted by time).
3. Cleaned data is saved for latest backtest run.
4. Dashboard sends strategy config using AJAX.
5. Django backtesting service generates trades.
6. Result and trades are saved in SQLite.
7. Results page reads latest result and shows metrics + trade table.
8. CSV export downloads the trade log.

---

## Screenshots

### Main Dashboard

![Kinetic Observatory Dashboard](ui%20screenshots/kinetic%20observatory%20dashboard.png)

### Strategy Dropdown

![Strategy Dropdown](ui%20screenshots/kinetic%20observatory%20strategy%20dropdown%20menu.png)

### Upload Page

![Upload Page](ui%20screenshots/kinetic%20observatory%20upload.png)

### Results Page

![Results Page](ui%20screenshots/kinetic%20observatory%20results%20page.png)

### Trade Log CSV Snapshot

![Trade CSV Snapshot](ui%20screenshots/result%20csv%20file%20excel%20file%20snapshot.png)

### Django Admin Login

![Django Admin Login](ui%20screenshots/django%20admin%20login.png)

### Django Admin Home

![Django Admin Home](ui%20screenshots/django%20admin%20homepage.png)

### Admin Backtest Results Table

![Admin Backtest Results](ui%20screenshots/djanog%20administration%20superuser%20backtest%20results.png)

---

## Run From Scratch (Windows, macOS, Linux)

### 0) Install Prerequisites

- Python 3.10 or newer
- Git
- Internet connection for package install

Check Python:

```bash
python --version
```

If `python` does not work on macOS/Linux, use:

```bash
python3 --version
```

### 1) Clone Project

```bash
git clone <your-repo-url>
cd stock-backtesting-platform-django-web-wpl-mini-project-finance-kinetic-observatory
```

### 2) Create and Activate Virtual Environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv venv
venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install Dependencies

Recommended (exact project dependencies):

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Manual install (if you want explicit package commands):

```bash
pip install django
pip install pandas numpy openpyxl xlrd
```

### 4) Move to Django Project Folder

Windows/macOS/Linux:

```bash
cd backend/core
```

### 5) Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6) Create Admin Superuser

```bash
python manage.py createsuperuser
```

Fill username, email, and password when prompted.

### 7) Run Tests (Optional but Recommended)

```bash
python manage.py test trading
```

### 8) Start Server

```bash
python manage.py runserver
```

Open in browser:

- App: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

If port 8000 is busy:

```bash
python manage.py runserver 8001
```

---

## How To Use The App Step-by-Step

1. Open **Upload** page.
2. Enter dataset label (optional).
3. Upload `.xlsx` file with OHLCV columns.
4. Click **Process file**.
5. Open **Dashboard** page.
6. Choose strategy (MA / RSI / EMA).
7. Enter parameters:
	 - MA: short window, long window
	 - RSI: RSI period
	 - EMA: EMA window
8. Click **Run Backtest**.
9. Open **Results** page to see:
	 - Capital used
	 - Total Profit/Loss
	 - Number of trades
	 - Win percent
	 - Trade table (entry/exit, quantity, capital allocated, profit)
10. Click **Download Trade Log** for CSV.

---

## Input File Format

Current upload supports only `.xlsx`.

Required columns (case-insensitive with alias support for date-like names):

- Date (or `timestamp`, `datetime`, `time`)
- Open
- High
- Low
- Close
- Volume

Example:

| Date | Open | High | Low | Close | Volume |
|---|---:|---:|---:|---:|---:|
| 2026-02-11 10:16:00 | 2962.2 | 2968.0 | 2960.4 | 2966.8 | 120000 |

---

## API Routes

UI pages:

- `/` -> Dashboard page
- `/upload-page/` -> Upload page
- `/results-page/` -> Results page

JSON/API endpoints:

- `POST /upload/` -> upload and validate dataset
- `POST /run-backtest/` -> run strategy backtest
- `POST /run-backtest-api/` -> API-style backtest endpoint
- `POST /backtest/` -> backward-compatible alias
- `GET /results/` -> latest/selected result JSON
- `GET /download-trades/` -> trade log CSV

---

## Project Structure

```text
backend/
	core/
		manage.py
		core/                # Django settings/urls/wsgi/asgi
		trading/             # Forms, models, views, backtesting services
		templates/trading/   # Dashboard, Upload, Results pages
		static/              # CSS + JS assets
		media/               # Uploaded datasets and latest cleaned CSV
data/
	raw/                  # Raw design/export assets (ignored in git)
docs/
README.md
requirements.txt
```

---

## Troubleshooting

### "python manage.py runserver" fails

- Ensure you are in `backend/core` folder.
- Ensure venv is activated.
- Run migrations:

```bash
python manage.py migrate
```

### Missing package error

```bash
python -m pip install -r requirements.txt
```

### Upload rejected

- Confirm file is `.xlsx`.
- Confirm required columns exist.
- Confirm date column values are parseable.

### No backtest result shown

- Upload file first.
- Then run backtest from Dashboard.
- Reload Results page.

---

## Tech Stack

- Backend: Django, Python
- Data: Pandas, NumPy
- File IO: openpyxl, xlrd
- DB: SQLite
- Frontend: HTML, CSS, Bootstrap 5, JavaScript, jQuery AJAX

---

## Future Improvements

- Add true short-selling strategy mode.
- Add multi-strategy comparison in one run.
- Add equity curve chart and drawdown metrics.
- Add brokerage/slippage model.
- Add live market API integration.

---

## License

This project is intended for academic and learning use.
