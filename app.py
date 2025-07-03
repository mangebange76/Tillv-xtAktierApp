import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import time

# Autentisering till Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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
HEADER = ["Ticker", "Tillväxt 2027 (%)", "P/S TTM", "Målkurs 2027", "Senast uppdaterad"]

# Försök öppna eller skapa Google Sheet
try:
    SPREADSHEET = client.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    SPREADSHEET = client.create(SHEET_NAME)
    SPREADSHEET.share(credentials_dict["client_email"], perm_type="user", role="writer")

sheet = SPREADSHEET.sheet1

# Kontrollera om rubriker finns
existing_data = sheet.get_all_values()
if not existing_data or existing_data[0] != HEADER:
    sheet.clear()
    sheet.append_row(HEADER)

# Funktioner
def load_data():
    rows = sheet.get_all_records()
    return pd.DataFrame(rows)

def add_ticker(ticker, tillvaxt):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheetet saknar kolumnen 'Ticker'")
        return
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    ps_ttm, mal = calculate_valuation(ticker, tillvaxt)
    if ps_ttm is None:
        st.error("Kunde inte hämta data.")
        return
    sheet.append_row([ticker, tillvaxt, ps_ttm, mal, pd.Timestamp.today().strftime("%Y-%m-%d")])
    st.success(f"{ticker} tillagd!")

def calculate_valuation(ticker, tillvaxt):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.quarterly_financials.T
        revs = stock.quarterly_financials.loc["Total Revenue"]
        if revs.shape[0] < 4:
            return None, None
        revenue_ttm = sum(revs.iloc[:4])
        shares = stock.info.get("sharesOutstanding")
        price = stock.info.get("currentPrice")
        if not revenue_ttm or not shares or not price:
            return None, None
        ps_ttm = round((price * shares) / revenue_ttm, 2)
        tillv_factor = (1 + float(tillvaxt) / 100) ** 3
        mal = round((revenue_ttm * tillv_factor / shares) * ps_ttm, 2)
        return ps_ttm, mal
    except Exception:
        return None, None

def delete_ticker(ticker):
    data = sheet.get_all_records()
    for i, row in enumerate(data):
        if row["Ticker"] == ticker:
            sheet.delete_rows(i + 2)
            st.success(f"{ticker} borttagen.")
            return
    st.warning(f"{ticker} hittades inte.")

# Streamlit-gränssnitt
st.title("📊 Aktieanalys – Målkurs 2027")

with st.form("add_form"):
    new_ticker = st.text_input("Ticker (t.ex. AAPL)").upper().strip()
    tillv = st.number_input("Förväntad tillväxt 2027 (%)", step=1.0)
    submitted = st.form_submit_button("➕ Lägg till bolag")
    if submitted and new_ticker and tillv:
        add_ticker(new_ticker, tillv)

df = load_data()
if not df.empty:
    st.subheader("📈 Analys")
    sort_col = st.selectbox("Sortera efter", df.columns)
    st.dataframe(df.sort_values(by=sort_col, ascending=False))

    st.subheader("🗑️ Ta bort bolag")
    ticker_to_delete = st.selectbox("Välj bolag", df["Ticker"])
    if st.button("Ta bort"):
        delete_ticker(ticker_to_delete)
else:
    st.info("⚠️ Inga bolag tillagda ännu.")
