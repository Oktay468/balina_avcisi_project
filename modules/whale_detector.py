import pandas as pd


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI indikatörünü hesaplar."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def detect_whale_activity(
    df: pd.DataFrame,
    volume_multiplier: float = 2.5,
    max_price: float = 7.0,
) -> dict:
    """Multi-Filter Balina Analizi (Fiyat Üst Sınırı Destekli)."""
    if df.empty or len(df) < 5:
        return {
            "detected": False,
            "score": 0,
            "close_price": 0,
            "vol_ratio": 0,
            "rsi": 0,
            "price_change_pct": 0,
            "reasons": "Yetersiz Seans Verisi",
            "target_1pct": 0,
            "target_2pct": 0,
        }

    latest = df.iloc[-1]
    close_price = latest["Close"]

    # FİYAT FİLTRESİ: Son fiyat belirlenen limitin (Örn: 7$) üzerindeyse direkt elenir
    if close_price > max_price:
        return {
            "detected": False,
            "score": 0,
            "close_price": round(close_price, 2),
            "vol_ratio": 0,
            "rsi": 0,
            "price_change_pct": 0,
            "reasons": f"Fiyat Limiti Üstünde (>{max_price})",
            "target_1pct": 0,
            "target_2pct": 0,
        }

    lookback = min(20, len(df) - 1)
    prev_bars = df.iloc[-(lookback + 1) : -1]

    # Hacim & Fiyat Değişimi
    avg_vol = prev_bars["Volume"].mean()
    curr_vol = latest["Volume"]
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
    price_change_pct = (
        (latest["Close"] - latest["Open"]) / latest["Open"]
    ) * 100

    # İndikatörler
    df["EMA_50"] = df["Close"].ewm(span=min(50, len(df)), adjust=False).mean()
    df["RSI"] = calculate_rsi(df["Close"], min(14, len(df) - 1))

    latest_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
    latest_ema = df["EMA_50"].iloc[-1] if "EMA_50" in df else close_price

    score = 0
    reasons = []
    has_volume_spike = False

    # Kriter A: Hacim Patlaması (ZORUNLU)
    if vol_ratio >= volume_multiplier:
        has_volume_spike = True
        score += 30
        reasons.append(f"Hacim Patlaması ({round(vol_ratio, 1)}x)")

    # Kriter B: Pozitif Mum
    if price_change_pct > 0:
        score += 20
        reasons.append("Pozitif Mum")

    # Kriter C: Trend Onayı
    if close_price >= latest_ema:
        score += 20
        reasons.append("Trend Yukarı (EMA+)")

    # Kriter D: RSI
    if 40 <= latest_rsi <= 70:
        score += 15
        reasons.append(f"RSI İdeal ({round(latest_rsi, 1)})")

    # Kriter E: Güçlü Kapanış
    candle_range = latest["High"] - latest["Low"]
    if (
        candle_range > 0
        and (latest["Close"] - latest["Low"]) / candle_range > 0.65
    ):
        score += 15
        reasons.append("Güçlü Kapanış")

    is_high_probability = (score >= 70) and has_volume_spike

    return {
        "detected": is_high_probability,
        "score": score,
        "close_price": round(close_price, 2),
        "vol_ratio": round(vol_ratio, 2),
        "rsi": round(latest_rsi, 1) if pd.notna(latest_rsi) else 0,
        "price_change_pct": round(price_change_pct, 2),
        "reasons": " | ".join(reasons) if reasons else "Kriter Karşılanmadı",
        "target_1pct": round(close_price * 1.01, 2),
        "target_2pct": round(close_price * 1.02, 2),
    }
