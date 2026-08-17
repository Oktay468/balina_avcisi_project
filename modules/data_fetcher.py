import pandas as pd
import requests
import yfinance as yf


def get_all_market_tickers(market="BIST"):
    """Seçilen piyasaya göre tüm hisse sembollerini internetten dinamik çeker."""
    if market == "BIST":
        try:
            # BIST hisse listesini canlı kaynaktan çek
            url = "https://raw.githubusercontent.com/sh4rk/bist-hisseleri/main/bist_hisseleri.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    else:
        # ABD Borsası (SEC veritabanından dinamik çeker)
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            return [item["ticker"] for item in data.values()]
        except Exception:
            return []


def get_stock_data(
    ticker: str, market: str = "BIST", period: str = "5d", interval: str = "15m"
) -> pd.DataFrame:
    """Belirtilen hissenin mum verilerini çeker."""
    try:
        symbol = (
            f"{ticker}.IS"
            if (market == "BIST" and not ticker.endswith(".IS"))
            else ticker
        )

        stock = yf.Ticker(symbol)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return None
