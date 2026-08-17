import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from modules.data_fetcher import fetch_stock_data, get_all_market_tickers
from modules.whale_detector import detect_whale_activity

load_dotenv()

st.set_page_config(
    page_title="Balina Avcısı - Alpaca Entegre Radar",
    page_icon="🐋",
    layout="wide",
)

st.title("🐋 Balina Avcısı - Alpaca Entegre & Multi-Filter Radar")
st.caption(
    "Alpaca API desteği ile canlı borsa takibi ve çoklu süzgeçli balina analizi."
)

# --- SIDEBAR ---
st.sidebar.header("⚙️ Tarama Ayarları")

alpaca_key = os.getenv("ALPACA_API_KEY")
if alpaca_key:
    st.sidebar.success("🟢 Alpaca API Bağlı (Canlı Veri)")
else:
    st.sidebar.warning("🟡 Alpaca Key Bulunamadı (Gecikmeli Veri)")

market_type = st.sidebar.radio(
    "İşlem Yapılacak Piyasa:",
    options=["BIST", "ABD Borsası (US)"],
    index=1,
)
market_code = "BIST" if market_type == "BIST" else "US"
currency = "TL" if market_code == "BIST" else "$"

with st.sidebar.status("Dış Kaynaktan Hisseler Çekiliyor...", expanded=False):
    all_tickers = get_all_market_tickers(market_type=market_code)

st.sidebar.info(f"Dış kaynaktan **{len(all_tickers)}** adet hisse yüklendi.")

scan_limit = st.sidebar.slider(
    "Taranacak Hisse Adedi:",
    min_value=10,
    max_value=min(len(all_tickers), 1000) if all_tickers else 100,
    value=50,
    step=10,
)

vol_multiplier = st.sidebar.slider(
    "Hacim Patlaması Hassasiyeti (Kat):",
    min_value=1.5,
    max_value=10.0,
    value=2.5,
    step=0.5,
)

# --- ANA EKRAN ---
if st.button("🔍 Canlı Taramayı Başlat", type="primary"):
    selected_tickers = all_tickers[:scan_limit]

    st.divider()
    st.subheader(
        f"📊 {market_type} Taraması ({len(selected_tickers)} Hisse Analiz"
        " Ediliyor)"
    )

    with st.expander("👁️ Taranan Hisse Sembollerini Gör"):
        st.write(", ".join(selected_tickers))

    progress_bar = st.progress(0)
    results = []

    for idx, symbol in enumerate(selected_tickers):
        df = fetch_stock_data(symbol, market_type=market_code)
        if not df.empty:
            res = detect_whale_activity(df, volume_multiplier=vol_multiplier)
            res["ticker"] = symbol.upper()
            results.append(res)

        progress_bar.progress((idx + 1) / len(selected_tickers))

    progress_bar.empty()

    if results:
        data_table = []
        for r in results:
            if r.get("close_price", 0) > 0:
                status = "🚨 BALİNA VAR!" if r["detected"] else "⚪ Normal"
                data_table.append(
                    {
                        "Hisse": r["ticker"],
                        "Durum": status,
                        "Güven Skoru": f"{r['score']} / 100",
                        f"Son Fiyat ({currency})": f"{r['close_price']} {currency}",
                        "Hacim Katı": f"{r['vol_ratio']}x",
                        "RSI": r["rsi"],
                        "Son Mum Değişimi": f"%{r['price_change_pct']}",
                        "Onay Detayları": r["reasons"],
                        f"%1 Hedef ({currency})": f"{r['target_1pct']} {currency}",
                        f"%2 Hedef ({currency})": f"{r['target_2pct']} {currency}",
                    }
                )

        res_df = pd.DataFrame(data_table)
        res_df = res_df.sort_values(by="Güven Skoru", ascending=False)
        st.dataframe(res_df, use_container_width=True)

        whales_found = [r for r in results if r.get("detected")]
        if whales_found:
            st.success(
                f"🔥 Toplam {len(whales_found)} hissede yüksek güvenlikli balina"
                " girişi tespit edildi!"
            )
            cols = st.columns(min(len(whales_found), 3))
            for i, w in enumerate(whales_found[:6]):
                with cols[i % 3]:
                    st.metric(
                        label=f"🚨 {w['ticker']} (Skor: {w['score']})",
                        value=f"{w['close_price']} {currency}",
                        delta=f"Hacim: {w['vol_ratio']}x",
                    )
        else:
            st.info(
                "Taranan hisselerde belirlenen yüksek kriterde balina girişi"
                " bulunamadı."
            )