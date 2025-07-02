import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Tillväxtaktier", layout="wide")

# Autentisering till Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Ange ditt Google Sheet-ID och bladnamn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Förväntade kolumner
EXPECTED_COLUMNS = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta", "Börsvärde", "Omsättning TTM",
    "P/S TTM snitt", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027",
    "Beräknad omsättning 2027", "Målkurs 2027"
]

# Ladda data från Google Sheet
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or not all(col in df.columns for col in EXPECTED_COLUMNS):
        st.warning("❌ Sheet saknar förväntade kolumner. Kontrollera rubriker.")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    return df

# Spara DataFrame till Google Sheet
def save_data(df):
    worksheet.clear()
    worksheet.append_row(EXPECTED_COLUMNS)
    rows = df[EXPECTED_COLUMNS].values.tolist()
    worksheet.append_rows(rows)

# Lägg till nytt bolag
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return

    try:
        ticker_data = yf.Ticker(ticker)
        info = ticker_data.info

        namn = info.get("shortName", "")
        valuta = info.get("financialCurrency", "")
        börsvärde = info.get("marketCap", "")
        omsättning_ttm = info.get("totalRevenue", "")

        hist = ticker_data.history(period="1d")
        nuvarande_kurs = round(hist["Close"].iloc[-1], 2) if not hist.empty else ""

        if not all([namn, valuta, börsvärde, omsättning_ttm, nuvarande_kurs]):
            st.error(f"❌ Kunde inte hämta data för {ticker}.")
            return

        ps_tal = börsvärde / omsättning_ttm if omsättning_ttm != 0 else None

        ny_rad = {
            "Ticker": ticker,
            "Namn": namn,
            "Nuvarande kurs": nuvarande_kurs,
            "Valuta": valuta,
            "Börsvärde": börsvärde,
            "Omsättning TTM": omsättning_ttm,
            "P/S TTM snitt": round(ps_tal, 2) if ps_tal else "",
            "Tillväxt 2025": "",
            "Tillväxt 2026": "",
            "Tillväxt 2027": "",
            "Beräknad omsättning 2027": "",
            "Målkurs 2027": ""
        }

        df = pd.concat([df, pd.DataFrame([ny_rad])], ignore_index=True)
        save_data(df)
        st.success(f"✅ {ticker} tillagt!")
    except Exception as e:
        st.error(f"Fel vid tillägg: {e}")

# Uppdatera befintligt bolag
def update_ticker(ticker):
    df = load_data()
    index = df.index[df["Ticker"] == ticker].tolist()
    if not index:
        st.warning(f"{ticker} finns inte.")
        return

    try:
        row = df.loc[index[0]]
        omsättning = float(row["Omsättning TTM"])
        ps_ttm = float(row["P/S TTM snitt"])
        g25 = float(row["Tillväxt 2025"]) / 100
        g26 = float(row["Tillväxt 2026"]) / 100
        g27 = float(row["Tillväxt 2027"]) / 100

        oms_2027 = omsättning * (1 + g25) * (1 + g26) * (1 + g27)
        mål_kurs = (oms_2027 / omsättning) * float(row["Nuvarande kurs"])

        df.at[index[0], "Beräknad omsättning 2027"] = round(oms_2027, 2)
        df.at[index[0], "Målkurs 2027"] = round(mål_kurs, 2)

        save_data(df)
        st.success(f"✅ {ticker} uppdaterad.")
    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")

# Huvudfunktion
def main():
    st.title("📈 Tillväxtaktier mot 2027")
    df = load_data()

    # Formulär för att lägga till nytt bolag
    st.subheader("Lägg till nytt bolag")
    new_ticker = st.text_input("Ange ticker (t.ex. AAPL, MSFT)")
    if st.button("Lägg till"):
        if new_ticker:
            add_ticker(new_ticker.strip().upper())
        else:
            st.warning("❗ Fyll i en ticker.")

    # Visa existerande bolag
    if not df.empty:
        st.subheader("🧾 Existerande bolag")
        st.dataframe(df, use_container_width=True)

        # Formulär för att uppdatera befintliga bolag
        st.subheader("🔄 Uppdatera tillväxt och målkurs")
        ticker_to_update = st.selectbox("Välj bolag att uppdatera", df["Ticker"])
        tillv_25 = st.number_input("Tillväxt 2025 (%)", value=0.0)
        tillv_26 = st.number_input("Tillväxt 2026 (%)", value=0.0)
        tillv_27 = st.number_input("Tillväxt 2027 (%)", value=0.0)
        if st.button("Uppdatera"):
            i = df.index[df["Ticker"] == ticker_to_update].tolist()[0]
            df.at[i, "Tillväxt 2025"] = tillv_25
            df.at[i, "Tillväxt 2026"] = tillv_26
            df.at[i, "Tillväxt 2027"] = tillv_27
            save_data(df)
            update_ticker(ticker_to_update)

if __name__ == "__main__":
    main()
