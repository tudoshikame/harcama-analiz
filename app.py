import streamlit as st
import pdfplumber
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Banka Hesap Özeti & Harcama Analiz Paneli",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Expanded Predefined Category Keywords Mapping
CATEGORY_KEYWORDS = {
    "Market & Süpermarket": [
        "MIGROS", "MİGROS", "CARREFOUR", "BIM", "BİM", "A101", "SOK", "ŞOK", "FILE", "FİLE", 
        "MAKRO", "TARIM KREDI", "TARIM KREDİ", "PEHLIVANOGLU", "PEHLİVANOĞLU", "KIM", "KİM", 
        "HAPPY CENTER", "TEKEL", "BAKKAL", "MANAV", "KASAP", "MARKET", "SAYIM", "MAMUL", 
        "GIDA", "CAGRI", "ÇAĞRI", "METRO GROSS", "BIZIM TOPTAN", "BİZİM TOPTAN", "KOMŞU MARKET", 
        "BİNGÖL KURUYEMİŞ", "BÜFE"
    ],
    "Yeme & İçme / Kahve": [
        "STARBUCKS", "ESPRESSOLAB", "KAHVE DUNYASI", "KAHVE DÜNYASI", "YEMEKSEPETI", "YEMEKSEPETİ", 
        "GETIR", "GETİR", "TRENDYOL YEMEK", "MCDONALDS", "BURGER KING", "DOMINOS", "DOMİNOS", 
        "RESTORAN", "LOKANTA", "CAFE", "KAFE", "DONER", "DÖNER", "KEBAP", "KOFTE", "KÖFTE", 
        "PIZZA", "PASTANE", "FIRIN", "SIMIT SARAYI", "TATLICI", "BOHÇACI", "KAHVE", "GURME", 
        "BAR", "BISTRO", "BİLTUR CATERING", "GÖNÜL BAHÇESİ CAFE", "GAZİANEP BAKLAMA", "KATIK GIDA", 
        "JALE AĞIRDAN", "KAHVE SANAT"
    ],
    "Akaryakıt & Ulaşım": [
        "SHELL", "OPET", "BP", "PETROL OFISI", "PETROL OFİSİ", "TOTAL", "TP", "AYGAZ", "UBER", 
        "TAKSI", "TAKSİ", "TAXI", "BITAKSI", "BİTAKSİ", "MARTI", "BINBIN", "BİNBİN", 
        "TCDD", "THY", "PEGASUS", "AJET", "ISTANBULKART", "İSTANBULKART", "HGS", "OGS", 
        "AKARYAKIT", "PETROL", "ULAŞIM", "METRO", "IZBAN", "İZBAN", "MARMARAY", "Otoyol", 
        "KOPRU", "KÖPRÜ", "TURKISH AIRLINES", "RENK PETROL", "COP PETROL", "ENUYGUN.COM"
    ],
    "Giyim & Spor & Alışveriş": [
        "DECATHLON", "BAUHAUS", "TRENDYOL", "TEKSAL", "SENJUTSU DOJO", "YUKİ", "HIGH STEP", 
        "HEPSIBURADA", "AMAZON", "N11", "CICEKSEPETI", "ÇİÇEKSEPETİ", "ZARA", "PULL&BEAR", 
        "BERSHKA", "STRADIVARIUS", "MANGO", "H&M", "BOYNER", "BEYMEN", "LCW", "LC WAIKIKI", 
        "DEFACTO", "MAVI", "MAVİ", "WATSONS", "GRATIS", "FLO", "MORHIPO", "TEKNOSA", "VATA", 
        "MEDIAMARKT", "TEKSAL TEKSTİL"
    ],
    "Abonelik & Dijital": [
        "NETFLIX", "SPOTIFY", "YOUTUBE", "APPLE", "GOOGLE", "STEAM", "PLAYSTATION", 
        "XBOX", "DISNEY", "BLUTV", "EXXEN", "GAIN", "OPENAI", "CHATGPT", "MIDJOURNEY", 
        "PRIME", "ICLOUD", "MICROSOFT", "TELEGRAM", "PAYCELL", "TURKCELL", "EA SWISS", 
        "TANGO LIVE", "İYZİCO", "SUPPLEMENTLER"
    ],
    "Fatura & Aidat": [
        "ENERJISA", "CK BOGAZICI", "BEDAS", "AYEDAS", "ISKI", "ASKI", "IGDAS", "BURSAGAZ", 
        "VODAFONE", "TURK TELEKOM", "TURKNET", "MILLENICOM", "DIGITURK", "D-SMART", 
        "AIDAT", "FATURA", "ELEKTRIK", "SU", "DOGALGAZ", "NETGSM"
    ],
    "Faiz & Masraf": [
        "DÖNEM FAİZİ", "DONEM FAIZI", "GECİKME FAİZİ", "GECIKME FAIZI", "FAİZ", "FAIZ", 
        "KOMİSYON", "KOMISYON", "ÜCRET", "UCRET", "HESAP İŞLETİM"
    ],
    "Ödeme / İade": [
        "ÖDEME", "ODEME", "İADE", "IADE", "MAHSUP", "ALACAK"
    ],
    "IBAN & Transferler": [
        "HAVALE", "EFT", "FAST", "VIRMAN", "TRANSFER", "IBAN", "GELEN", "GONDEREN", "GÖNDEREN", "ALICI"
    ],
    "Nakit İşlemleri": [
        "ATM", "NAKIT", "NAKİT", "PARA CEKME", "PARA ÇEKME", "CEKME", "ÇEKME", "MATRIKS"
    ]
}

def clean_text_tr(text):
    """Converts text to uppercase using Turkish locale handling."""
    if not text:
        return ""
    return str(text).replace('i', 'İ').replace('ı', 'I').upper()

def kategori_belirle(aciklama):
    """Categorizes a transaction based on description keywords."""
    desc_clean = clean_text_tr(aciklama)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Ödeme / İade":
            continue
        for kw in keywords:
            if clean_text_tr(kw) in desc_clean:
                return category
    return "Diğer Harcamalar"

AYLAR_REGEX = r'(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)'
TARIH_PATTERN = re.compile(rf'^\s*(\d{{1,2}}\s+{AYLAR_REGEX}\s+\d{{4}})', re.IGNORECASE)

def parse_pdf(file):
    islemler = []
    raw_debug_logs = []
    
    with pdfplumber.open(file) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            raw_debug_logs.append(f"--- Sayfa {page_num} ---")
            text = page.extract_text(layout=False)
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                raw_debug_logs.append(f"[Satır] {line_clean}")
                
                # Başlık, devir borcu ve toplam satırlarını baştan ele
                if any(x in line_clean.upper() for x in ["ÖNCEKİ DÖNEM HESAP ÖZETİ", "TOPLAM", "PUAN ÖZETİ", "DÖNEM İÇİ ALIŞVERİŞLERDEN"]):
                    continue
                
                # Taksit / kur ara bilgilendirme satırlarını ele
                if any(x in line_clean.upper() for x in ["TL'LİK İŞLEMIN", "TL'LİK İŞLEM", "TAKSİTLİ İŞLEM", "USD KARŞILIĞI", "TRY USD"]):
                    continue
                
                # Satır geçerli bir işlem tarihi ile başlamalı
                tarih_match = TARIH_PATTERN.search(line_clean)
                if not tarih_match:
                    continue
                
                tarih = tarih_match.group(1).strip()
                kalan_metin = line_clean[tarih_match.end():].strip()
                
                # Tutar çıkarma: Satır içindeki para formatlarını bul (+9.180,59 veya 650,31 vb.)
                tutarlar = re.findall(r'([+-]?\d{1,3}(?:\.\d{3})*,\d{2})', kalan_metin)
                if not tutarlar:
                    continue
                
                # İşlem tutarı genelde açıklamadan hemen sonraki ilk para değeridir
                raw_tutar = tutarlar[0]
                is_iade_or_payment = raw_tutar.startswith('+') or ('İADE' in kalan_metin.upper()) or ('İADESİ' in kalan_metin.upper()) or ('IADE' in kalan_metin.upper())
                
                # Açıklama metnini tutardan önceki kısım olarak al
                aciklama_kismi = kalan_metin.split(raw_tutar)[0].strip()
                # Temassız ikon metinlerini temizle
                aciklama_kismi = re.sub(r'^[^\w]+', '', aciklama_kismi).strip()
                
                # Sayısal tutar
                tutar_sayisal = abs(float(raw_tutar.replace('+', '').replace('-', '').replace('.', '').replace(',', '.')))
                
                # İşlem Türü belirleme
                if "ÖDEME-İNTERNET BANKACILIĞI" in aciklama_kismi.upper() or "ÖDEME - İNTERNET" in aciklama_kismi.upper() or ("ÖDEME" in aciklama_kismi.upper() and raw_tutar.startswith('+')):
                    islem_turu = "Kart Borç Ödemesi"
                elif is_iade_or_payment:
                    islem_turu = "Ödeme / İade"
                elif any(kw in clean_text_tr(aciklama_kismi) for kw in ["HAVALE", "EFT", "FAST", "TRANSFER", "IBAN", "VIRMAN"]):
                    islem_turu = "IBAN / Transfer"
                else:
                    islem_turu = "Kart Harcaması"
                
                islemler.append({
                    "Tarih": tarih,
                    "Açıklama": aciklama_kismi,
                    "Tutar": tutar_sayisal,
                    "İşlem Türü": islem_turu,
                    "Kategori": kategori_belirle(aciklama_kismi) if islem_turu == "Kart Harcaması" else islem_turu
                })

    df = pd.DataFrame(islemler)
    return df, raw_debug_logs

# Main Application Layout
st.title("💳 Banka Hesap Özeti & Harcama Analiz Paneli")
st.markdown("Harcama alışkanlıklarınızı otomatik analiz etmek, kategorize etmek ve incelemek için banka veya kredi kartı ekstrelerinizi PDF formatında yükleyin.")

# Sidebar File Upload & Controls
st.sidebar.header("📁 Veri Kaynağı")
uploaded_file = st.sidebar.file_uploader("Hesap Özeti PDF Yükle", type=["pdf"])

# Load Data
df = pd.DataFrame()
debug_logs = []

if uploaded_file is not None:
    with st.spinner("PDF ekstresi işleniyor..."):
        df, debug_logs = parse_pdf(uploaded_file)
        if df.empty:
            st.error("⚠️ PDF dosyasından hiç işlem okunamadı! Lütfen alttaki 'Ham Okunan Satırlar (Debug)' bölümünü kontrol edin.")
else:
    st.info("Lütfen sol panelden banka veya kredi kartı ekstre PDF dosyanızı yükleyin.")

# Debug Expander for Transparency
with st.expander("🔍 Ham Okunan Satırlar (Hata Ayıklama / Debug)"):
    if debug_logs:
        st.text(f"Toplam okunan ham satır sayısı: {len(debug_logs)}")
        st.code("\n".join(debug_logs[:300]), language="text")
        if len(debug_logs) > 300:
            st.caption("...(Çıktı uzun olduğu için ilk 300 satır gösteriliyor)...")
    else:
        st.info("Henüz yüklenmiş ve işlenmiş bir PDF bulunmuyor.")

if not df.empty:
    # Filter out previous period balance if present
    df = df[~df["Açıklama"].str.upper().str.contains("ÖNCEKİ DÖNEM HESAP ÖZETİ BORCU|ONCEKI DONEM HESAP OZETI BORCU", na=False)].copy()

    # Calculate metrics using the requested code snippet
    kart_harcamalari = df[df["İşlem Türü"] == "Kart Harcaması"]["Tutar"].sum()
    toplam_iade = df[df["İşlem Türü"] == "Ödeme / İade"]["Tutar"].sum()
    net_donem_harcamasi = kart_harcamalari - toplam_iade
    kart_borc_odemeleri = df[df["İşlem Türü"] == "Kart Borç Ödemesi"]["Tutar"].sum()
    iban_transferleri = df[df["İşlem Türü"] == "IBAN / Transfer"]["Tutar"].sum()

    # Sidebar Filters
    st.sidebar.header("🔍 Filtreler")
    all_categories = list(CATEGORY_KEYWORDS.keys()) + ["Diğer Harcamalar"]
    selected_categories = st.sidebar.multiselect("Kategoriye Göre Filtrele", options=all_categories, default=all_categories)
    
    selected_types = st.sidebar.multiselect("İşlem Türüne Göre Filtrele", options=["Kart Harcaması", "IBAN / Transfer", "Ödeme / İade", "Kart Borç Ödemesi"], default=["Kart Harcaması", "IBAN / Transfer", "Ödeme / İade", "Kart Borç Ödemesi"])
    
    # Apply Filters to main view dataframe
    filtered_df = df[
        df["Kategori"].isin(selected_categories) & 
        df["İşlem Türü"].isin(selected_types)
    ].copy()
    
    if filtered_df.empty:
        st.warning("Seçilen filtrelerle eşleşen işlem bulunamadı.")
    else:
        # Rename column for display consistency if needed
        display_df = filtered_df.rename(columns={"Tutar": "Tutar (TL)"}).reset_index(drop=True)
        
        # KPI Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Net Dönem Harcaması", f"₺{net_donem_harcamasi:,.2f}", f"Brüt: ₺{kart_harcamalari:,.2f} - İade: ₺{toplam_iade:,.2f}")
        with col2:
            st.metric("Kart Borç Ödemeleri", f"₺{kart_borc_odemeleri:,.2f}")
        with col3:
            st.metric("Toplam Kart Harcamaları", f"₺{kart_harcamalari:,.2f}")
        with col4:
            cat_grouped = display_df[(display_df['İşlem Türü'] == 'Kart Harcaması') & (display_df['Kategori'].isin(selected_categories))].groupby("Kategori")["Tutar (TL)"].sum()
            top_category = cat_grouped.idxmax() if not cat_grouped.empty else "N/A"
            top_category_val = cat_grouped.max() if not cat_grouped.empty else 0.0
            st.metric("En Çok Harcanan Kategori", top_category, f"₺{top_category_val:,.2f}")
            
        st.markdown("---")
        
        # Visual Analytics Section
        st.subheader("📊 Görsel Analiz")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("##### Kategoriye Göre Harcama Dağılımı")
            spending_charts_df = display_df[(display_df['İşlem Türü'] == 'Kart Harcaması') & (display_df['Kategori'].isin(selected_categories))].copy()
            if not spending_charts_df.empty:
                cat_summary = spending_charts_df.groupby("Kategori")["Tutar (TL)"].sum().reset_index()
                fig_donut = px.pie(
                    cat_summary, 
                    values="Tutar (TL)", 
                    names="Kategori", 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_donut.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Kategori grafiği için veri yok.")
                
        with chart_col2:
            st.markdown("##### İşlem Türü Dağılımı")
            type_summary_df = display_df[display_df['İşlem Türü'].isin(selected_types) & (display_df['İşlem Türü'] != 'Kart Borç Ödemesi')].copy()
            if not type_summary_df.empty:
                type_summary = type_summary_df.groupby("İşlem Türü")["Tutar (TL)"].sum().reset_index()
                fig_bar = px.bar(
                    type_summary,
                    x="İşlem Türü",
                    y="Tutar (TL)",
                    color="İşlem Türü",
                    text_auto=True,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("İşlem türü grafiği için veri yok.")
                
        st.markdown("---")
        
        # Interactive Data Grid & Categorization Editor
        st.subheader("📝 Harcama ve İşlem Listesi")
        st.markdown("Herhangi bir işlem yanlış kategorize edildiyse, aşağıdaki tablodan kategorileri doğrudan düzenleyebilirsiniz.")
        
        category_options = list(CATEGORY_KEYWORDS.keys()) + ["Diğer Harcamalar"]
        
        edited_df = st.data_editor(
            display_df,
            column_config={
                "Tarih": st.column_config.TextColumn("Tarih", disabled=True),
                "Açıklama": st.column_config.TextColumn("Açıklama", disabled=True),
                "Kategori": st.column_config.SelectboxColumn(
                    "Kategori",
                    help="Doğru harcama kategorisini seçin",
                    options=category_options,
                    required=True
                ),
                "İşlem Türü": st.column_config.SelectboxColumn(
                    "İşlem Türü",
                    help="İşlem Türü",
                    options=["Kart Harcaması", "IBAN / Transfer", "Ödeme / İade", "Kart Borç Ödemesi"],
                    required=True
                ),
                "Tutar (TL)": st.column_config.NumberColumn("Tutar (TL)", format="₺%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Export Option
        st.markdown("---")
        st.subheader("💾 Analiz Edilen Veriyi Dışa Aktar")
        
        csv_data = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 CSV Olarak İndir",
            data=csv_data,
            file_name="harcama_analiz_raporu.csv",
            mime="text/csv",
            type="primary"
        )
else:
    st.info("Lütfen sol panelden banka veya kredi kartı ekstre PDF dosyanızı yükleyin.")
