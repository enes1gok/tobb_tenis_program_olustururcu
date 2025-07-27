import streamlit as st
import gspread
from oauth2client.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- Google Sheets Bağlantısı ---
service_account_info = st.secrets["google_service_account"]

# Google Sheets API yetkilendirme
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)

# Google Sheet bağlantısı
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1EMwasKdHp8otQ0Rxeu0qqGg6RSj30DhjlDK4dCA37aA/edit?usp=sharing")
worksheet = spreadsheet.sheet1

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
hours = [f"{h:02d}:00" for h in range(9, 21)]

st.set_page_config(page_title="Tenis Ders Takvimi", layout="wide")
st.title("🎾 TOBB Tenis Ders Takvimi")

# --- Seçili seansı tut ---
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

# --- Takvim ---
st.subheader("📅 Haftalık Takvim")
calendar_cols = st.columns(len(days))
max_capacity = 6

for i, day in enumerate(days):
    with calendar_cols[i]:
        st.markdown(f"**{day}**")
        for hour in hours:
            session_df = data[(data["Gün"] == day) & (data["Saat"] == hour)]
            count = len(session_df)
            key = f"{day}-{hour}"

            seviye_raw = session_df.iloc[0]["Seviye"] if not session_df.empty else "-"
            seviye = f"{seviye_raw}"

            durum_emoji = "🟢" if count < max_capacity else "🔴"
            label = f"{durum_emoji} {hour}\n{seviye} | {count}/{max_capacity}"

            # ✅ Tıklanabilirlik kontrolü
            clicked = st.button(label, key=key, disabled=(count >= max_capacity))
            if clicked:
                st.session_state.selected_session = (day, hour)

# --- Kayıt Formu (sadece seans seçildiyse görünür) ---
if "selected_session" in st.session_state and st.session_state["selected_session"]:
    st.markdown("---")
    st.subheader("📝 Seans Kaydı")

    selected_day, selected_hour = st.session_state.selected_session
    session_df = data[(data["Gün"] == selected_day) & (data["Saat"] == selected_hour)]
    count = len(session_df)
    seviye = session_df.iloc[0]["Seviye"] if not session_df.empty else "-"
    durum_emoji = "🟢 Müsait" if count < max_capacity else "🔴 Dolu"

    # Seans bilgileri kutusu
    st.markdown(
        f"""
        <div style="background-color:#000000; padding:10px; border-radius:10px; border:1px solid #ddd">
            <b>📅 Seçilen Seans:</b> {selected_day} - {selected_hour}<br/>
            <b>🎯 Seviye:</b> <span style='color:gold'><b>{seviye}</b></span><br/>
            <b>👥 Kayıt Sayısı:</b> {count}/{max_capacity}<br/>
            <b>📌 Durum:</b> {durum_emoji}
        </div>
        """, unsafe_allow_html=True
    )

    # Kayıt formu
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            ad = st.text_input("Ad")
            soyad = st.text_input("Soyad")
        with col2:
            seviye_input = st.selectbox("Seviye", ["Başlangıç", "Orta", "İleri"])

        submitted = st.form_submit_button("Kaydı Tamamla")

        if submitted:
            # Güncel doluluğu tekrar kontrol et
            current_data = get_data()
            count = len(current_data[(current_data["Gün"] == selected_day) & (current_data["Saat"] == selected_hour)])
            if count >= max_capacity:
                st.error("❌ Bu seans artık dolu. Lütfen başka bir saat seçin.")
            else:
                # Kayıt eklendikten sonra:
                worksheet.append_row([ad, soyad, seviye_input, selected_day, selected_hour, str(datetime.now())])
                get_data.clear()  # 👈 önbelleği sıfırla
                st.success(f"✅ Kayıt başarıyla alındı: {selected_day} - {selected_hour}")
                st.session_state.selected_session = None
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
