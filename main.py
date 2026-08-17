import random
import pandas as pd
import streamlit as st

# Modül içe aktarımları
from modules.data_fetcher import get_all_market_tickers, get_stock_data
from modules.whale_detector import detect_whale_activity

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Balina Avcısı - BIST & US Radar", page_icon="🐋", layout="wide"
)

st.title("🐋 Balina Avcısı - Hacim & Fiyat Radarı")
st.caption("Piyasada sessizce toplanan hisseleri anlık tespit edin.")

# --- SIDEBAR (TARAMA AYARLARI) ---
st.sidebar.header("⚙️ Tarama Ayarları")

market = st.sidebar.radio(
    "İşlem Yapılacak Piyasa:", options=["BIST", "ABD Borsası (US)"], index=0
)

scan_limit = st.sidebar.slider(
    "Taranacak Hisse Adedi:", min_value=10, max_value=200, value=50, step=10
)

vol_multiplier = st.sidebar.slider(
    "Hacim Patlaması Hassasiyeti (Kat):",
    min_value=1.5,
    max_value=10.0,
    value=4.5,
    step=0.25,
)

# Seçilen piyasaya göre varsayılan tavan fiyat ve para birimi
price_unit = "TL" if market == "BIST" else "$"
default_max_price = 100.0 if market == "BIST" else 7.0

max_price_limit = st.sidebar.number_input(
    f"Maksimum Hisse Fiyatı ({price_unit}):",
    min_value=0.5,
    max_value=5000.0,
    value=default_max_price,
    step=1.0,
    help="Belirlenen fiyatın üzerindeki hisseler taramaya alınmaz.",
)

random_scan = st.sidebar.checkbox(
    "Hisseleri Rastgele Seç (A-Z Sırasını Boz)",
    value=True,
    help="İşaretlenirse tüm piyasa içinden rastgele hisse seçer, sadece 'A' harfindekilere takılmanızı engeller.",
)

# --- TARAMA MANTIĞI ---
if st.sidebar.button("🔍 Canlı Taramayı Başlat", type="primary"):
    st.info("Piyasa verileri çekiliyor ve analiz ediliyor...")

    # 1. Sembolleri Çek
    all_tickers = get_all_market_tickers(market=market)

    if not all_tickers:
        st.error(
            "Hisse listesi alınamadı. Lütfen internet / API bağlantısını kontrol edin."
        )
        st.stop()

    # 2. Hisse Seçimi (Rastgele veya Sıralı)
    if random_scan:
        selected_tickers = random.sample(
            all_tickers, min(scan_limit, len(all_tickers))
        )
    else:
        selected_tickers = all_tickers[:scan_limit]

    # 3. Analiz Döngüsü
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, ticker in enumerate(selected_tickers):
        status_text.text(
            f"Analiz ediliyor ({idx + 1}/{len(selected_tickers)}): {ticker}"
        )

        df = get_stock_data(ticker, market=market)
        if df is not None and not df.empty:
            res = detect_whale_activity(
                df, volume_multiplier=vol_multiplier, max_price=max_price_limit
            )
            res["ticker"] = ticker
            results.append(res)

        progress_bar.progress((idx + 1) / len(selected_tickers))

    status_text.empty()
    progress_bar.empty()

    # 4. Sonuçları Ekrana Basma
    if results:
        res_df = pd.DataFrame(results)
        detected_df = res_df[res_df["detected"] == True]

        st.subheader(
            f"🔥 Toplam {len(detected_df)} hissede yüksek güvenlikli balina girişi tespit edildi!"
        )

        if not detected_df.empty:
            # Öne Çıkarılan Kartlar
            cols = st.columns(min(3, len(detected_df)))
            for idx, (_, row) in enumerate(detected_df.iterrows()):
                with cols[idx % 3]:
                    st.metric(
                        label=f"🚨 {row['ticker']} (Skor: {row['score']})",
                        value=f"{row['close_price']} {price_unit}",
                        delta=f"Hacim: {row['vol_ratio']}x",
                    )
                    st.caption(f"Neden: {row['reasons']}")

            st.divider()

            # Detaylı Tablo Görünümü
            st.write("### 📊 Tespit Edilen Hisselerin Detaylı Listesi")
            display_cols = [
                "ticker",
                "score",
                "close_price",
                "vol_ratio",
                "price_change_pct",
                "rsi",
                "reasons",
            ]
            st.dataframe(
                detected_df[display_cols].rename(
                    columns={
                        "ticker": "Hisse",
                        "score": "Skor",
                        "close_price": f"Fiyat ({price_unit})",
                        "vol_ratio": "Hacim Katı",
                        "price_change_pct": "Değişim %",
                        "rsi": "RSI",
                        "reasons": "Sinyal Nedenleri",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.warning(
                "Belirlenen hacim katı ve fiyat limiti kriterlerine uyan hisse bulunamadı."
            )

        # Taranan Tüm Hisseleri İncelemek İçin Akordeon
        with st.expander("📋 Taranan Tüm Hisselerin Sonuçlarını İncele"):
            st.dataframe(res_df, use_container_width=True)
    else:
        st.error("Veri çekilebildi fakat analiz edilecek geçerli mum bulunamadı.")
