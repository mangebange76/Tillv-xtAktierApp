import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Inställningar
SPREADSHEET_NAME = "Aktieanalys"
SHEET_NAME = "Blad1"

@st.cache_data(ttl=60)
def load_sheet():
    try:
        sh = gc.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(SPREADSHEET_NAME)
    try:
        worksheet = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=SHEET_NAME, rows="100", cols="20")

    data = worksheet.get_all_values()
    if not data or data[0] != [
        "Ticker", "Namn", "Nuvarande kurs", "Valuta",
        "Omsättning TTM", "P/S TTM",
        "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027",
        "Omsättning 2027", "Målkurs 2027"
    ]:
        worksheet.update("A1:K1", [[
            "Ticker", "Namn", "Nuvarande kurs", "Valuta",
            "Omsättning TTM", "P/S TTM",
            "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027",
            "Omsättning 2027", "Målkurs 2027"
        ]])
        return pd.DataFrame(columns=[
            "Ticker", "Namn", "Nuvarande kurs", "Valuta",
            "Omsättning TTM", "P/S TTM",
            "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027",
            "Omsättning 2027", "Målkurs 2027"
        ])
    return pd.DataFrame(data[1:], columns=data[0])

def save_sheet(df):
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.worksheet(SHEET_NAME)
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def calculate_projection(row):
    try:
        revenue = float(row["Omsättning TTM"])
        growth_25 = float(row["Tillväxt 2025"]) / 100
        growth_26 = float(row["Tillväxt 2026"]) / 100
        growth_27 = float(row["Tillväxt 2027"]) / 100
        ps = float(row["P/S TTM"])
        shares = None  # Placeholder om vi vill räkna ut per aktie
        projected_revenue = revenue * (1 + growth_25) * (1 + growth_26) * (1 + growth_27)
        price_target = projected_revenue * ps
        return round(projected_revenue, 2), round(price_target, 2)
    except Exception as e:
        return "", ""

def update_all_data(df):
    updated_rows = []
    for index, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get("shortName", "")
            price = info.get("currentPrice", "")
            currency = info.get("currency", "")
            shares_out = info.get("sharesOutstanding")
            revenue_ttm = info.get("totalRevenue")

            if revenue_ttm and shares_out:
                market_cap = shares_out * price if price else None
                ps_ttm = round(market_cap / revenue_ttm, 2) if market_cap else ""
            else:
                ps_ttm = ""

            df.at[index, "Namn"] = name
            df.at[index, "Nuvarande kurs"] = price
            df.at[index, "Valuta"] = currency
            df.at[index, "Omsättning TTM"] = revenue_ttm
            df.at[index, "P/S TTM"] = ps_ttm

            projected_revenue, price_target = calculate_projection(df.loc[index])
            df.at[index, "Omsättning 2027"] = projected_revenue
            df.at[index, "Målkurs 2027"] = price_target

        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")
    return df

def add_ticker(ticker, df):
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return df

    new_row = {
        "Ticker": ticker,
        "Namn": "", "Nuvarande kurs": "", "Valuta": "",
        "Omsättning TTM": "", "P/S TTM": "",
        "Tillväxt 2025": "10", "Tillväxt 2026": "10", "Tillväxt 2027": "10",
        "Omsättning 2027": "", "Målkurs 2027": ""
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Aktieanalys", layout="wide")
st.title("📈 Aktieanalys – målkurs baserat på tillväxt och P/S")

df = load_sheet()

# Tickerinmatning
new_ticker = st.text_input("Lägg till ticker (t.ex. AAPL)")
if st.button("Lägg till") and new_ticker:
    df = add_ticker(new_ticker.strip().upper(), df)
    save_sheet(df)
    st.success("Ticker tillagd.")

# Uppdatera alla
if st.button("🔄 Uppdatera data för alla tickers"):
    df = update_all_data(df)
    save_sheet(df)
    st.success("Alla tickers uppdaterade.")

# Visa tabell
if df.empty:
    st.info("Inga tickers tillagda ännu.")
else:
    st.dataframe(df)
