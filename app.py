import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Anslut till Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Kontrollera rubrikraden
def ensure_headers():
    existing = worksheet.row_values(1)
    expected = ["Ticker", "Namn", "Valuta", "Omsättning TTM", "Marknadsvärde", "Antal aktier", "P/S snitt", "Tillväxt 2027 (%)", "Omsättning 2027", "Målkurs 2027"]
    if existing != expected:
        worksheet.update('A1:K1', [expected])

ensure_headers()

# Ladda data från Google Sheet
def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Lägg till ny ticker
def add_ticker(ticker):
    df = load_data()
    if "Ticker" in df.columns and ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    info = yf.Ticker(ticker).info
    if "shortName" not in info:
        st.error(f"Kunde inte hämta data för {ticker}")
        return
    namn = info.get("shortName", "")
    valuta = info.get("currency", "")
    marketcap = info.get("marketCap", 0)
    shares_outstanding = info.get("sharesOutstanding", 0)
    revenue_ttm = info.get("totalRevenue", 0)
    if not all([marketcap, shares_outstanding, revenue_ttm]):
        st.error(f"Inkomplett data för {ticker}")
        return
    ps_ttm = marketcap / revenue_ttm if revenue_ttm else 0
    new_row = [ticker, namn, valuta, revenue_ttm, marketcap, shares_outstanding, ps_ttm, "", "", ""]
    worksheet.append_row(new_row)
    st.success(f"{ticker} tillagd!")

# Uppdatera data för alla tickers
def update_all():
    df = load_data()
    updated = []
    for index, row in df.iterrows():
        try:
            ticker = row["Ticker"]
            info = yf.Ticker(ticker).info
            revenue = info.get("totalRevenue", 0)
            marketcap = info.get("marketCap", 0)
            shares = info.get("sharesOutstanding", 0)
            ps = marketcap / revenue if revenue else 0
            tillvaxt = row["Tillväxt 2027 (%)"]
            tillvaxt = float(tillvaxt) if tillvaxt != "" else 0
            oms_2027 = revenue * (1 + tillvaxt / 100) if revenue else 0
            malkurs = oms_2027 / shares * ps if shares else 0
            worksheet.update_cell(index + 2, 4, revenue)
            worksheet.update_cell(index + 2, 5, marketcap)
            worksheet.update_cell(index + 2, 6, shares)
            worksheet.update_cell(index + 2, 7, ps)
            worksheet.update_cell(index + 2, 9, oms_2027)
            worksheet.update_cell(index + 2, 10, malkurs)
            updated.append(ticker)
        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {row['Ticker']}: {e}")
    if updated:
        st.success(f"✅ Uppdaterade: {', '.join(updated)}")

# Streamlit-gränssnitt
st.title("📊 Aktieanalys med målkurs 2027")
new_ticker = st.text_input("Lägg till en ny ticker (t.ex. AAPL)")

if st.button("Lägg till ticker"):
    if new_ticker:
        add_ticker(new_ticker.strip().upper())
    else:
        st.warning("Ange en ticker.")

if st.button("🔁 Uppdatera alla bolag"):
    update_all()

df = load_data()
if df.empty:
    st.info("Inga bolag tillagda ännu.")
else:
    st.subheader("Analyserade bolag:")
    st.dataframe(df)
