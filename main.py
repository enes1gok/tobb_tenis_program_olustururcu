import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- Google Sheets Bağlantısı ---
service_account_info = st.secrets["google_service_account"]

# Google Sheets API yetkilendirme
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)

# Google Sheet bağlantısı
try:
    spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1EMwasKdHp8otQ0Rxeu0qqGg6RSj30DhjlDK4dCA37aA/edit?usp=sharing")
    worksheet = spreadsheet.sheet1
except Exception as e:
    st.error(f"Google Sheet'e bağlanırken hata oluştu: {e}")

@st.cache_data(ttl=300)
def get_data():
    try:
        rows = worksheet.get_all_values()
        expected_columns = ["Ad", "Soyad", "Seviye", "Gün", "Saat", "Zaman"]

        if not rows:
            return pd.DataFrame(columns=expected_columns)

        if rows[0] == expected_columns:
            return pd.DataFrame(rows[1:], columns=rows[0])
        else:
            return pd.DataFrame(rows, columns=expected_columns)
    except Exception as e:
        st.error(f"Google Sheets bağlantı hatası: {e}")
        return pd.DataFrame(columns=["Ad", "Soyad", "Seviye", "Gün", "Saat", "Zaman"])

data = get_data()

# Günler ve Saatler
days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
time_slots = [datetime.strptime(f"{h}:{m:02d}", "%H:%M") for h in range(7, 22) for m in [0, 15, 30, 45]] # saat aralığını dilediğin gibi ayarla
max_capacity = 6

st.set_page_config(page_title="Tenis Ders Takvimi", layout="wide")
st.title("🎾 TOBB Tenis Ders Takvimi")

# --- Seçili seansı tut ---
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

st.subheader("📅 Haftalık Takvim")
calendar_cols = st.columns(len(days))

for i, day in enumerate(days):
    with calendar_cols[i]:
        st.markdown(f"**{day}**")
        for hour in time_slots:
            session_df = data[(data["Gün"] == day) & (data["Saat"] == hour)]
            count = len(session_df)
            seviye = session_df.iloc[0]["Seviye"] if not session_df.empty else "-"
            label = f"{hour.strftime('%H:%M')}<br/><span style='font-size:12px'>{seviye if count > 0 else ''}</span><br/><b>{count}/{max_capacity}</b>"
            # Renk & buton durumu
            if count == 0:
                # Hiç kayıt olmayan saat: gösterilmesin
                st.markdown(
                    f"<div style='border:1px dashed #CCC; padding:6px; border-radius:6px; margin-bottom:6px; background:#F9F9F9; text-align:center; color:#999'>{hour.strftime('%H:%M')}</div>",
                    unsafe_allow_html=True
                )
            else:
                box_color = "#D4EDDA" if count < max_capacity else "#F8D7DA"
                text_color = "#155724" if count < max_capacity else "#721C24"
                border_color = "#C3E6CB" if count < max_capacity else "#F5C6CB"

                clicked = st.button(
                    label="",
                    key=f"{day}_{hour}",
                    help=f"{day} {hour} - {seviye} - {count}/{max_capacity}",
                    args=(day, hour),
                )

                st.markdown(
                    f"""
                    <div style='background-color:{box_color}; color:{text_color}; border:2px solid {border_color};
                                border-radius:8px; padding:6px; text-align:center; margin-bottom:6px'>
                        {label}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if clicked:
                    st.session_state.selected_session = (day, hour)

st.subheader("📝 Seans Kaydı")

with st.form("register_form"):
    col1, col2 = st.columns(2)

    with col1:
        ad = st.text_input("Ad")
        soyad = st.text_input("Soyad")
        seviye = st.selectbox("Seviye", ["Başlangıç", "Orta", "İleri"])

    with col2:
        gün = st.selectbox("Gün", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"])
        baslangic_saat = st.time_input("Başlangıç Saati")
        bitis_saat = st.time_input("Bitiş Saati")

    submitted = st.form_submit_button("Kaydı Tamamla")

    if submitted:
        if bitis_saat <= baslangic_saat:
            st.error("❌ Bitiş saati, başlangıç saatinden sonra olmalıdır.")
        elif not ad or not soyad:
            st.warning("Lütfen tüm bilgileri eksiksiz doldurun.")
        else:
            # Veriyi kaydet (örnek):
            worksheet.append_row([
                ad, soyad, seviye, gün,
                baslangic_saat.strftime("%H:%M"),
                bitis_saat.strftime("%H:%M"),
                str(datetime.now())
            ])
            get_data.clear()
            st.success(f"✅ Kayıt alındı: {gün} {baslangic_saat.strftime('%H:%M')} - {bitis_saat.strftime('%H:%M')}")
            st.rerun()

# --- Kayıt Listesi ---
st.markdown("---")
st.subheader("📋 Kayıt Listesi")

if data.empty:
    st.info("Henüz hiçbir kayıt bulunmamaktadır.")
else:
    for i, row in data.iterrows():
        cols = st.columns([2, 2, 2, 2, 2, 3, 1])
        cols[0].write(row["Ad"])
        cols[1].write(row["Soyad"])
        cols[2].write(row["Seviye"])
        cols[3].write(row["Gün"])
        cols[4].write(row["Saat"])
        cols[5].write(row["Zaman"])

        # Benzersiz buton için key
        delete_key = f"delete_{i}"

        if cols[6].button("🗑️", key=delete_key):
            worksheet.delete_rows(i + 2)
            get_data.clear()
            st.success(f"{row['Ad']} {row['Soyad']} kaydı silindi.")
            st.rerun()
