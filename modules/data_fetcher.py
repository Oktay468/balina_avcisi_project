import pandas as pd
import requests
import yfinance as yf


def get_all_market_tickers(market="BIST"):
    """Seçilen piyasaya göre hisse sembol listesini getirir."""
    if market == "BIST":
        # Popüler BIST hisselerinden oluşan örnek liste
        return [
            "THYAO",
            "GARAN",
            "ASELS",
            "EREGL",
            "AKBNK",
            "SISE",
            "KCHOL",
            "TUPRS",
            "BIMAS",
            "SAHOL",
            "YKBNK",
            "ISCTR",
            "EKGYO",
            "HEKTS",
            "SASA",
            "KORDS",
            "PETKM",
            "ASTOR",
            "KONTR",
            "ALARK",
            "AHSGY",
            "AKFGY",
            "AKMGY",
            "ALKLC",
            "ARASE",
            "ARDYZ",
            "ANELE",
            "AHGAZ",
        ]
    else:
        # ABD Borsası (SEC veritabanından tüm canlı sembolleri çeker)
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            tickers = [item["ticker"] for item in data.values()]
            return tickers
        except Exception:
            # Bağlantı koparsa yedek ABD hisse listesi
            return [
                "AAPL",
                "NVDA",
                "TSLA",
                "AMZN",
                "MSFT",
                "AMD",
                "GOOGL",
                "META",
                "PLTR",
                "SOFI",
            ]


def get_stock_data(
    ticker: str, market: str = "BIST", period: str = "5d", interval: str = "15m"
) -> pd.DataFrame:
    """Belirtilen hissenin mum verilerini çeker."""
    try:
        # BIST hisseleri yfinance tarafında .IS uzantısı gerektirir
        symbol = (
            f"{ticker}.IS"
            if (market == "BIST" and not ticker.endswith(".IS"))
            else ticker
        )

        stock = yf.Ticker(symbol)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return None

        # Sütun isimlerini standartlaştırma
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return None
