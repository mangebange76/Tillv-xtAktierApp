import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import json

# Autentisering till Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Inställningar
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
HEADER = ["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"]

# Öppna kalkylarket och bladet
sh = client.open_by_key(SHEET_ID)
try:
    worksheet = sh.worksheet(SHEET_NAME)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_NAME, rows="1000", cols="20")

# Skapa rubrikrad om den saknas
existing_data = worksheet.get_all_values()
if not existing_data or existing_data[0] != HEADER:
    worksheet.update("A1", [HEADER])

def load_data():
    rows = worksheet.get_all_records()
    df = pd.DataFrame(rows)
    return df

def save_data(df):
    worksheet.clear()
    worksheet.update("A1", [df.columns.tolist()])
    worksheet.update("A2", df.values.tolist())

def calculate_target_price(row):
    try:
        oms_ttm = float(row["Omsättning TTM"])
        marketcap = float(row["Nuvarande kurs"]) * 1  # Dummy multiplikation
        ps_ttm = marketcap / oms_ttm if oms_ttm else 0

        tillv_25 = float(row.get("Tillväxt 2025", 0))
        tillv_26 = float(row.get("Tillväxt 2026", 0))
        tillv_27 = float(row.get("Tillväxt 2027", 0))
        tillväxt_faktor = (1 + tillv_25/100) * (1 + tillv_26/100) * (1 + tillv_27/100)

        oms_2027 = oms_ttm * tillväxt_faktor
        mål = ps_ttm * oms_2027

        return pd.Series([ps_ttm, oms_2027, mål])
    except Exception:
        return pd.Series([None, None, None])

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    try:
        info = yf.Ticker(ticker).info
        namn = info.get("shortName", "Okänt")
        kurs = info.get("currentPrice")
        valuta = info.get("currency")
        oms_ttm = info.get("totalRevenue")
        tillv_25 = info.get("revenueGrowth", 0) * 100
        tillv_26 = tillv_25
        tillv_27 = 10

        ny_rad = pd.DataFrame([{
            "Ticker": ticker,
            "Namn": namn,
            "Nuvarande kurs": kurs,
            "Valuta": valuta,
            "Omsättning TTM": oms_ttm,
            "Tillväxt 2025": tillv_25,
            "Tillväxt 2026": tillv_26,
            "Tillväxt 2027": tillv_27,
        }])

        ps, oms_2027, målkurs = calculate_target_price(ny_rad.iloc[0])
        ny_rad["P/S TTM"] = ps
        ny_rad["Omsättning 2027"] = oms_2027
        ny_rad["Målkurs 2027"] = målkurs

        df = pd.concat([df, ny_rad], ignore_index=True)
        save_data(df)
        st.success(f"{ticker} har lagts till.")
    except Exception as e:
        st.error(f
