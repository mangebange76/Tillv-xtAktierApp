import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets autentisering
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file"]

credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
sheet = gc.open_by_url(SPREADSHEET_URL).sheet1

# Funktioner
def load_data():
    rows = sheet.get_all_values()
    if not rows:
        return pd.DataFrame(columns=["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM",
                                     "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"])
    headers = rows[0]
    data = rows[1:]
    return pd.DataFrame(data, columns=headers)

def save_data(df):
    sheet.clear()
    sheet.append_row(df.columns.tolist())
    for row in df.values.tolist():
        sheet.append_row(row)

def fetch_and_calculate(ticker, tillv_2027):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("shortName", "")
        price = info.get("currentPrice", "")
        currency = info.get("currency", "")
        shares = info.get("sharesOutstanding", None)

        if not shares:
            return None

        hist = stock.quarterly_financials
        revenue = hist.loc["Total Revenue"] if "Total Revenue" in hist.index else None
        if revenue is None or revenue.empty:
            return None

        # Hämta TTM omsättning
        ttm_revenue = revenue.iloc[:, :4].sum()
        ps_ttm = price / (ttm_revenue / shares)

        # Tillväxt
        tillv_2025 = info.get("earningsGrowth", 0) or 0
        tillv_2026 = info.get("revenueGrowth", 0) or 0

        oms_2027 = ttm_revenue * (1 + float(tillv_2025)) * (1 + float(tillv_2026)) * (1 + float(tillv_2027))
        målpris = (oms_2027 / shares) * ps_ttm

        return {
            "Ticker": ticker,
            "Namn": name,
            "Nuvarande kurs": round(price, 2),
            "Valuta": currency,
            "Omsättning TTM": round(ttm_revenue, 0),
            "P/S TTM": round(ps_ttm, 2),
            "Tillväxt 2025": round(float(tillv_2025), 2),
            "Tillväxt 2026": round(float(tillv_2026), 2),
            "Tillväxt 2027": round(float(tillv_2027), 2),
            "Omsättning 2027": round(oms_2027, 0),
            "Målkurs 2027": round(målpris, 2)
        }
    except:
        return None

# Gränssnitt
st.title("🎯 Aktieanalys med P/S och tillväxt")

df = load_data()

ticker = st.text_input("Ange ticker (t.ex. AAPL):").upper()
tillv_2027 = st.number_input("Förväntad tillväxt 2027 (%)", value=10.0) / 100

if st.button("Lägg till/uppdatera bolag"):
    result = fetch_and_calculate(ticker, tillv_2027)
    if result:
        result_df = pd.DataFrame([result])
        df = df[df["Ticker"] != ticker]
        df = pd.concat([df, result_df], ignore_index=True)
        save_data(df)
        st.success(f"{ticker} har lagts till eller uppdaterats.")
    else:
        st.error(f"Kunde inte hämta data för {ticker}.")

if not df.empty:
    st.dataframe(df)
