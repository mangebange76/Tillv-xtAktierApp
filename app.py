import streamlit as st
import pandas as pd
import yfinance as yf
from google.oauth2.service_account import Credentials
import gspread
import json

st.set_page_config(page_title="📊 Aktieanalys", layout="centered")

# Autentisering mot Google Sheets via secrets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials_dict = {
    "type": st.secrets["GOOGLE_CREDENTIALS"]["type"],
    "project_id": st.secrets["GOOGLE_CREDENTIALS"]["project_id"],
    "private_key_id": st.secrets["GOOGLE_CREDENTIALS"]["private_key_id"],
    "private_key": st.secrets["GOOGLE_CREDENTIALS"]["private_key"],
    "client_email": st.secrets["GOOGLE_CREDENTIALS"]["client_email"],
    "client_id": st.secrets["GOOGLE_CREDENTIALS"]["client_id"],
    "auth_uri": st.secrets["GOOGLE_CREDENTIALS"]["auth_uri"],
    "token_uri": st.secrets["GOOGLE_CREDENTIALS"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["GOOGLE_CREDENTIALS"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["GOOGLE_CREDENTIALS"]["client_x509_cert_url"],
    "universe_domain": st.secrets["GOOGLE_CREDENTIALS"]["universe_domain"]
}
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

SHEET_NAME = "Aktieanalys"
WORKSHEET_NAME = "Blad1"

# Ladda data
def load_data():
    try:
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(SHEET_NAME).add_worksheet(title=WORKSHEET_NAME, rows="100", cols="20")
        sheet.append_row(["Ticker", "Namn", "Valuta", "Nuvarande kurs", "Omsättning TTM", "Börsvärde", "Antal aktier", "P/S TTM", "Tillväxt 2027 (%)", "Målkurs 2027", "Senast uppdaterad"])
    rows = sheet.get_all_records()
    return pd.DataFrame(rows)

# Spara ny rad
def add_ticker(ticker, tillv):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheetet är tomt eller har fel rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        namn = info.get("shortName", "")
        valuta = info.get("currency", "")
        kurs = info.get("currentPrice", 0.0)
        shares = info.get("sharesOutstanding", 0)
        marketcap = info.get("marketCap", 0)
        revenue_ttm = info.get("totalRevenue", 0)

        if not all([kurs, shares, marketcap, revenue_ttm]):
            st.error("❌ Ofullständig data hämtad.")
            return

        ps_ttm = marketcap / revenue_ttm if revenue_ttm else 0
        tillv_factor = 1 + tillv / 100
        revenue_2027 = revenue_ttm * (tillv_factor ** 3)
        målpris = (revenue_2027 / shares) * ps_ttm
        datum = pd.Timestamp.now().strftime("%Y-%m-%d")

        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        sheet.append_row([ticker, namn, valuta, kurs, revenue_ttm, marketcap, shares, ps_ttm, tillv, målpris, datum])
        st.success(f"{ticker} tillagd!")
    except Exception as e:
        st.error(f"Fel vid hämtning: {e}")

# Visa app
st.title("📈 Aktieanalys: Målkurs 2027")

df = load_data()

with st.expander("➕ Lägg till nytt bolag"):
    new_ticker = st.text_input("Ange ticker (t.ex. AAPL)").strip().upper()
    tillv = st.number_input("Förväntad tillväxt 2027 (%)", min_value=-100.0, max_value=500.0, value=10.0)
    if st.button("Lägg till"):
        if new_ticker:
            add_ticker(new_ticker, tillv)

if not df.empty:
    st.subheader("📋 Bolagsdata")
    st.dataframe(df)

    with st.expander("🗑️ Ta bort bolag"):
        if "Ticker" in df.columns:
            ticker_to_delete = st.selectbox("Välj bolag att ta bort", df["Ticker"])
            if st.button("Ta bort"):
                sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
                cell = sheet.find(ticker_to_delete)
                sheet.delete_rows(cell.row)
                st.success(f"{ticker_to_delete} borttagen.")
        else:
            st.warning("Ingen 'Ticker'-kolumn hittades.")
else:
    st.info("Inga bolag inlagda ännu.")
