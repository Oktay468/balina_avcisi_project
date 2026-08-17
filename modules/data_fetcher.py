import os
from datetime import datetime, timedelta
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


def get_all_market_tickers(market_type: str = "BIST") -> list[str]:
    """Tüm borsa sembollerini TradingView API ve SEC üzerinden canlı çeker."""
    tickers = []

    if market_type == "BIST":
        # TradingView Canlı Türkiye Borsa Taraması (Tüm Aktif BIST Hisseleri)
        url = "https://scanner.tradingview.com/turkey/scan"
        payload = {
            "filter": [
                {"left": "type", "operation": "equal", "right": "stock"}
            ],
            "options": {"active_minds_only": False},
            "symbols": {"query": {"types": []}},
            "sort": {"sortBy": "name", "sortOrder": "asc"},
            "range": [0, 600],
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                tickers = [
                    item["s"].split(":")[-1]
                    for item in data.get("data", [])
                    if "s" in item
                ]
        except Exception as e:
            print(f"TradingView BIST canlı liste çekilemedi: {e}")

    else:
        # ABD (SEC Resmi Şirket Listesi)
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {
            "User-Agent": "BalinaAvcisiApp/1.0 (contact@balinaavcisi.com)"
        }
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                tickers = [v["ticker"] for v in data.values() if "ticker" in v]
        except Exception as e:
            print(f"ABD canlı liste çekilemedi: {e}")

    # Sembol Temizleme
    clean_tickers = []
    for t in tickers:
        if isinstance(t, str):
            symbol = t.strip().upper().replace(".", "-")
            if symbol and symbol.replace("-", "").isalnum():
                clean_tickers.append(symbol)

    return list(dict.fromkeys(clean_tickers))


def fetch_stock_data(symbol: str, market_type: str = "BIST") -> pd.DataFrame:
    """Alpaca API veya yfinance üzerinden sadece 5m canlı seans verisini çeker."""
    if market_type == "US" and ALPACA_API_KEY and ALPACA_SECRET_KEY:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame

            client = StockHistoricalDataClient(
                ALPACA_API_KEY, ALPACA_SECRET_KEY
            )
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol.upper(),
                timeframe=TimeFrame.Minute,
                start=datetime.now() - timedelta(days=1),
            )
            bars = client.get_stock_bars(request_params)
            df = bars.df
            if not df.empty:
                if isinstance(df.index, pd.MultiIndex):
                    df = df.xs(symbol.upper(), level="symbol")
                return df.rename(
                    columns={
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                    }
                )
        except Exception as e:
            print(f"Alpaca veri çekme hatası ({symbol}): {e}")

    # BIST veya yfinance (Sadece bugünün 5 dakikalık mumları, günlük veri fallback yok)
    clean_symbol = symbol.upper().replace(".IS", "")
    ticker_symbol = (
        f"{clean_symbol}.IS" if market_type == "BIST" else clean_symbol
    )

    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1d", interval="5m")
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()