import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering till Google Sheets via Streamlit Secrets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Ange Google Sheet
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Förväntade rubriker i första raden
expected_headers = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "Börsvärde",
    "Antal aktier", "P/S snitt TTM", "Målkurs 2027",
    "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)"
]

def ensure_headers():
    current_headers = worksheet.row_values(1)
    if current_headers != expected_headers:
        worksheet.clear()
        worksheet.insert_row(expected_headers, 1)

def load_data():
    ensure_headers()
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def save_data(df):
    worksheet.clear()
    worksheet.insert_row(expected_headers, 1)
    rows = df.astype(str).values.tolist()
    worksheet.append_rows(rows)

def fetch_financials(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info

        name = info.get("shortName", "")
        price = info.get("currentPrice", None)
        currency = info.get("financialCurrency", "")
        shares = info.get("sharesOutstanding", None)
        market_cap = info.get("marketCap", None)

        # Hämta kvartalsdata och beräkna TTM-omsättning
        quarters = ticker_obj.quarterly_income_stmt
        if quarters is not None and not quarters.empty:
            quarters = quarters.T
            quarters.index = pd.to_datetime(quarters.index)
            quarters = quarters.sort_index(ascending=False)
            ttm_revenue = quarters["Total Revenue"].iloc[:4].sum()
        else:
            ttm_revenue = None

        # Beräkna P/S TTM
        ps_ttm = (market_cap / ttm_revenue) if ttm_revenue and market_cap else None

        return {
            "Namn": name,
            "Nuvarande kurs": price,
            "Valuta": currency,
            "Omsättning TTM": ttm_revenue,
            "Börsvärde": market_cap,
            "Antal aktier": shares,
            "P/S snitt TTM": ps_ttm
        }
    except Exception as e:
        st.error(f"❌ Fel vid hämtning av data för {ticker}: {e}")
        return {}

def beräkna_målkurs(omsättning_ttm, tillväxt_25, tillväxt_26, tillväxt_27, antal_aktier, ps_snitt):
    try:
        oms_2027 = omsättning_ttm * (1 + tillväxt_25 / 100) * (1 + tillväxt_26 / 100) * (1 + tillväxt_27 / 100)
        return (oms_2027 / antal_aktier) * ps_snitt
    except:
        return None

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
