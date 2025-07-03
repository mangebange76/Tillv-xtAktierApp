import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets autentisering
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Ange ditt Google Sheet ID och kalkylbladets namn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
worksheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Förväntade kolumner
HEADERS = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta",
    "Omsättning TTM", "P/S TTM",
    "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027",
    "Omsättning 2027", "Målkurs 2027"
]

# Säkerställ att rubriker finns
def ensure_headers():
    values = worksheet.row_values(1)
    if values != HEADERS:
        worksheet.clear()
        worksheet.insert_row(HEADERS, 1)

# Läs data
def load_data():
    ensure_headers()
    rows = worksheet.get_all_records()
    return pd.DataFrame(rows)

# Lägg till nytt bolag
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    worksheet.append_row([ticker] + [""] * (len(HEADERS) - 1))
    st.success(f"{ticker} tillagd!")

# Uppdatera data för ett enskilt bolag
def update_row(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        df = load_data()

        name = info.get("shortName", "")
        price = info.get("currentPrice", "")
        currency = info.get("currency", "")
        shares_out = info.get("sharesOutstanding", None)
        revenue_ttm = info.get("totalRevenue", None)

        if not shares_out or not revenue_ttm or not price:
            st.error(f"❌ Saknas data för {ticker}.")
            return

        ps_ttm = round((shares_out * price) / revenue_ttm, 2)

        # Tillväxt från användare eller default
        tillvaxt_25 = st.number_input(f"{ticker} - Tillväxt 2025 (%)", value=10.0, key=f"25_{ticker}")
        tillvaxt_26 = st.number_input(f"{ticker} - Tillväxt 2026 (%)", value=10.0, key=f"26_{ticker}")
        tillvaxt_27 = st.number_input(f"{ticker} - Tillväxt 2027 (%)", value=10.0, key=f"27_{ticker}")

        oms_2027 = revenue_ttm * (1 + tillvaxt_25 / 100) * (1 + tillvaxt_26 / 100) * (1 + tillvaxt_27 / 100)
        mal_kurs = round((oms_2027 / shares_out) * ps_ttm, 2)

        # Hitta radnummer
        row_num = df.index[df["Ticker"] == ticker].tolist()
        if not row_num:
            st.error(f"❌ Kunde inte hitta {ticker} i bladet.")
            return
        row_index = row_num[0] + 2

        updated_row = [
            ticker, name, price, currency,
            revenue_ttm, ps_ttm,
            tillvaxt_25, tillvaxt_26, tillvaxt_27,
            round(oms_2027), mal_kurs
        ]
        worksheet.update(f"A{row_index}:K{row_index}", [updated_row])
        st.success(f"{ticker} uppdaterad.")
    except Exception as e:
        st.error(f"Fel vid uppdatering av {ticker}: {e}")

# Huvudfunktion
def main():
    st.title("📈 Aktieanalys 2027")
    df = load_data()

    # Lägg till ticker
    new_ticker = st.text_input("Lägg till ny ticker")
    if st.button("➕ Lägg till") and new_ticker:
        add_ticker(new_ticker.strip().upper())

    # Bläddra bolag
    if df.empty:
        st.info("Inga bolag inlagda ännu.")
        return

    index = st.number_input("Bolag #", min_value=1, max_value=len(df), value=1, step=1)
    selected = df.iloc[index - 1]
    st.write("### 📊 Data för", selected["Ticker"])
    st.dataframe(pd.DataFrame([selected]))

    if st.button(f"🔁 Uppdatera {selected['Ticker']}"):
        update_row(selected["Ticker"])

if __name__ == "__main__":
    main()
