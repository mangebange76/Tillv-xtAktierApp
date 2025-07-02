import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Google Sheets Setup ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Sheet info
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# --- Funktioner ---
def load_data():
    try:
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            st.warning("❌ Google Sheet är tomt.")
        return df
    except Exception as e:
        st.error(f"❌ Fel vid inläsning: {e}")
        return pd.DataFrame()

def save_data(df):
    try:
        worksheet.clear()
        worksheet.append_row(df.columns.tolist())
        worksheet.append_rows(df.values.tolist())
    except Exception as e:
        st.error(f"❌ Fel vid sparande: {e}")

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return
    new_row = {
        "Ticker": ticker,
        "Tillväxt 2027 (%)": "",
        "Valuta": "",
        "Omsättning (TTM)": "",
        "Börsvärde": "",
        "Antal aktier": "",
        "P/S TTM": "",
        "Målkurs 2027": "",
        "Senast uppdaterad": ""
    }
    df = df.append(new_row, ignore_index=True)
    save_data(df)
    st.success(f"{ticker} tillagd!")

def uppdatera_bolag(ticker):
    df = load_data()
    if ticker not in df["Ticker"].values:
        st.error(f"{ticker} finns inte i datan.")
        return

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")
        currency = info.get("currency", "USD")
        market_cap = info.get("marketCap", None)
        shares = info.get("sharesOutstanding", None)

        # Hämta kvartalsomsättning
        quarterly_rev = stock.quarterly_financials.loc["Total Revenue"]
        if quarterly_rev.empty or len(quarterly_rev) < 4:
            st.warning(f"❌ För lite data för {ticker}")
            return

        oms_ttm = quarterly_rev.iloc[:4].sum()
        ps_ttm = market_cap / oms_ttm if oms_ttm > 0 else None

        tillväxt = df.loc[df["Ticker"] == ticker, "Tillväxt 2027 (%)"].values[0]
        if tillväxt in ["", None]:
            st.warning(f"⚠️ Tillväxt för {ticker} saknas.")
            return

        tillväxt = float(tillväxt) / 100
        oms_2027 = oms_ttm * (1 + tillväxt) ** 3
        målpris = (oms_2027 / shares) * ps_ttm if shares else None

        # Uppdatera
        df.loc[df["Ticker"] == ticker, "Omsättning (TTM)"] = round(oms_ttm, 2)
        df.loc[df["Ticker"] == ticker, "P/S TTM"] = round(ps_ttm, 2)
        df.loc[df["Ticker"] == ticker, "Målkurs 2027"] = round(målpris, 2)
        df.loc[df["Ticker"] == ticker, "Börsvärde"] = market_cap
        df.loc[df["Ticker"] == ticker, "Antal aktier"] = shares
        df.loc[df["Ticker"] == ticker, "Valuta"] = currency
        df.loc[df["Ticker"] == ticker, "Senast uppdaterad"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        save_data(df)
        st.success(f"{ticker} uppdaterad!")
    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")

# --- Gränssnitt ---
st.title("📊 Aktieanalys – Målkurs 2027")

df = load_data()

new_ticker = st.text_input("Lägg till nytt ticker (t.ex. AAPL)")
if st.button("Lägg till"):
    if new_ticker:
        add_ticker(new_ticker.strip().upper())

if not df.empty and "Ticker" in df.columns:
    st.subheader("✅ Bolag i analys")
    for i, row in df.iterrows():
        ticker = row["Ticker"]
        st.write(f"**{ticker}**")
        if st.button(f"Uppdatera {ticker}", key=f"btn_{ticker}"):
            uppdatera_bolag(ticker)
else:
    st.info("Ingen data att visa.")
