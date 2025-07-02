import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# 🛡️ Autentisering till Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# 📄 Ange rätt Sheet ID och namn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

# 🧠 Anslut till rätt worksheet
spreadsheet = gc.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet(SHEET_NAME)

# 🧮 Funktion för att ladda data från sheet
def load_data():
    rows = worksheet.get_all_records()
    if not rows:
        return pd.DataFrame(columns=["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"])
    return pd.DataFrame(rows)

# ➕ Lägg till ny ticker
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    new_row = {"Ticker": ticker}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    worksheet.clear()
    worksheet.append_row(df.columns.tolist())
    for i in range(len(df)):
        worksheet.append_row(df.iloc[i].fillna("").tolist())

# 🔁 Uppdatera data för enskild ticker
def update_ticker_data(ticker):
    try:
        info = yf.Ticker(ticker).info
        hist = yf.Ticker(ticker).history(period="1d")
        price = round(hist["Close"].iloc[-1], 2)
        currency = info.get("currency", "")
        name = info.get("shortName", "")
        shares_outstanding = info.get("sharesOutstanding", None)
        revenue_ttm = info.get("totalRevenue", None)

        df = load_data()
        tillv_2025 = df.loc[df["Ticker"] == ticker, "Tillväxt 2025"].values[0]
        tillv_2026 = df.loc[df["Ticker"] == ticker, "Tillväxt 2026"].values[0]
        tillv_2027 = df.loc[df["Ticker"] == ticker, "Tillväxt 2027"].values[0]

        if isinstance(tillv_2025, str): tillv_2025 = float(tillv_2025.replace(",", "."))
        if isinstance(tillv_2026, str): tillv_2026 = float(tillv_2026.replace(",", "."))
        if isinstance(tillv_2027, str): tillv_2027 = float(tillv_2027.replace(",", "."))

        oms_2027 = revenue_ttm * (1 + tillv_2025/100) * (1 + tillv_2026/100) * (1 + tillv_2027/100)
        ps_ttm = (price * shares_outstanding) / revenue_ttm if revenue_ttm and shares_outstanding else None
        målpris_2027 = (oms_2027 / shares_outstanding) * ps_ttm if ps_ttm and shares_outstanding else None

        df.loc[df["Ticker"] == ticker, "Namn"] = name
        df.loc[df["Ticker"] == ticker, "Nuvarande kurs"] = price
        df.loc[df["Ticker"] == ticker, "Valuta"] = currency
        df.loc[df["Ticker"] == ticker, "Omsättning TTM"] = revenue_ttm
        df.loc[df["Ticker"] == ticker, "P/S TTM"] = round(ps_ttm, 2) if ps_ttm else ""
        df.loc[df["Ticker"] == ticker, "Omsättning 2027"] = round(oms_2027, 0)
        df.loc[df["Ticker"] == ticker, "Målkurs 2027"] = round(målpris_2027, 2) if målpris_2027 else ""

        worksheet.clear()
        worksheet.append_row(df.columns.tolist())
        for i in range(len(df)):
            worksheet.append_row(df.iloc[i].fillna("").tolist())

    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")

# 🚀 Huvudfunktion
def main():
    st.title("📈 Aktieanalys – Målkurs 2027")
    df = load_data()

    # ➕ Lägg till ny ticker
    new_ticker = st.text_input("Lägg till ny ticker:")
    if st.button("Lägg till"):
        if new_ticker.strip() != "":
            add_ticker(new_ticker.strip().upper())

    # 🔄 Uppdatera alla
    if st.button("🔁 Uppdatera alla bolag"):
        for ticker in df["Ticker"]:
            update_ticker_data(ticker)

    st.write("### Nuvarande analys:")
    st.dataframe(load_data())

if __name__ == "__main__":
    main()
