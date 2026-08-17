import os
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


def get_all_market_tickers(market_type: str = "BIST") -> list[str]:
    """Tüm borsa sembollerini dinamik canlı kaynaklardan çeker."""
    tickers = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if market_type == "BIST":
        urls = [
            "https://raw.githubusercontent.com/yusufogunc/bist-hisseleri/main/bist_hisseleri.json",
            "https://raw.githubusercontent.com/shubhraprakash/bist-100-tickers/main/bist100.txt"
        ]
        
        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200 and not res.text.startswith("404") and "<html" not in res.text.lower():
                    if url.endswith(".json"):
                        data = res.json()
                        tickers = data if isinstance(data, list) else list(data.keys())
                    else:
                        tickers = [line.strip() for line in res.text.splitlines() if line.strip()]
                    if tickers:
                        break
            except Exception as e:
                print(f"BIST URL bağlantı hatası ({url}): {e}")

    else:
        urls = [
            "https://www.sec.gov/files/company_tickers.json",
            "https://raw.githubusercontent.com/rreche/stock-symbol/main/symbols/us_symbols.json"
        ]
        sec_headers = {"User-Agent": "BalinaAvcisiApp/1.0 (contact@balinaavcisi.com)"}
        
        for url in urls:
            try:
                h = sec_headers if "sec.gov" in url else headers
                res = requests.get(url, headers=h, timeout=5)
                if res.status_code == 200 and not res.text.startswith("404") and "<html" not in res.text.lower():
                    data = res.json()
                    if "sec.gov" in url and isinstance(data, dict):
                        tickers = [item["ticker"] for item in data.values() if "ticker" in item]
                    elif isinstance(data, list):
                        tickers = [item["symbol"] if isinstance(item, dict) else str(item) for item in data]
                    if tickers:
                        break
            except Exception as e:
                print(f"ABD URL bağlantı hatası ({url}): {e}")

    clean_tickers = []
    for t in tickers:
        if isinstance(t, str):
            symbol = t.strip().upper().replace(".", "-")
            if symbol and "404" not in symbol and len(symbol) <= 10 and symbol.replace("-", "").isalnum():
                clean_tickers.append(symbol)

    return list(dict.fromkeys(clean_tickers))


def fetch_stock_data(symbol: str, market_type: str = "BIST") -> pd.DataFrame:
    """Alpaca API veya yfinance üzerinden hisse verisini çeker (Çift Katmanlı Fallback)."""
    if market_type == "US" and ALPACA_API_KEY and ALPACA_SECRET_KEY:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from datetime import datetime, timedelta

            client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol.upper(),
                timeframe=TimeFrame.Minute,
                start=datetime.now() - timedelta(days=5),
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

    # BIST veya yfinance kullanımı
    clean_symbol = symbol.upper().replace(".IS", "")
    ticker_symbol = f"{clean_symbol}.IS" if market_type == "BIST" else clean_symbol

    try:
        ticker = yf.Ticker(ticker_symbol)
        # 1. Öncelik: 5 dakikalık periyot
        df = ticker.history(period="5d", interval="5m")
        
        # 2. Öncelik: 5m boşsa veya yetersizse günlük periyoda geç
        if df.empty or len(df) < 15:
            df = ticker.history(period="1mo", interval="1d")

        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
