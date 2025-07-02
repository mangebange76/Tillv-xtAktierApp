import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering med Google Sheets via st.secrets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

# Funktion för att läsa data
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    expected_cols = ["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM",
                     "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"]
    if df.empty or list(df.columns) != expected_cols:
        st.error("❌ Sheet saknar rätt kolumner. Kontrollera rubriker i rad 1.")
        st.stop()
    return df

# Funktion för att spara data
def save_data(df):
    sheet.clear()
    sheet.append_row(df.columns.tolist())
    for _, row in df.iterrows():
        sheet.append_row(row.astype(str).tolist())

# Funktion för att hämta data och uppdatera för ett bolag
def update_ticker(ticker):
    try:
        ticker = ticker.strip().upper()
        stock = yf.Ticker(ticker)

        info = stock.info
        hist = stock.history(period="1y", interval="3mo")

        name = info.get("shortName", "Okänt")
        currency = info.get("currency", "N/A")
        current_price = info.get("currentPrice", 0.0)

        shares_outstanding = info.get("sharesOutstanding", None)
        if shares_outstanding is None:
            st.warning(f"⚠️ Kunde inte hämta antal aktier för {ticker}")
            return None

        quarterly_rev = stock.quarterly_financials
        if quarterly_rev.empty:
            st.warning(f"⚠️ Ingen kvartalsomsättning hittad för {ticker}")
            return None

        revenues = quarterly_rev.loc["Total Revenue"].values[:4]
        if len(revenues) < 4 or any(pd.isna(revenues)):
            st.warning(f"⚠️ Omsättningsdata saknas eller är ofullständig för {ticker}")
            return None

        revenue_ttm = sum(revenues)
        ps_ttm = (current_price * shares_outstanding) / revenue_ttm if revenue_ttm else None

        tillvaxt_2025 = st.session_state.get("tillvaxt_2025", 10.0)
        tillvaxt_2026 = st.session_state.get("tillvaxt_2026", 10.0)
        tillvaxt_2027 = st.session_state.get("tillvaxt_2027", 10.0)

        oms_2027 = revenue_ttm * (1 + tillvaxt_2025/100) * (1 + tillvaxt_2026/100) * (1 + tillvaxt_2027/100)
        malkurs_2027 = (oms_2027 / shares_outstanding) * ps_ttm if shares_outstanding else None

        return {
            "Ticker": ticker,
            "Namn": name,
            "Nuvarande kurs": round(current_price, 2),
            "Valuta": currency,
            "Omsättning TTM": round(revenue_ttm, 2),
            "P/S TTM": round(ps_ttm, 2),
            "Tillväxt 2025": tillvaxt_2025,
            "Tillväxt 2026": tillvaxt_2026,
            "Tillväxt 2027": tillvaxt_2027,
            "Omsättning 2027": round(oms_2027, 2),
            "Målkurs 2027": round(malkurs_2027, 2)
        }

    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")
        return None

# Lägg till nytt bolag
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning("⚠️ Bolaget finns redan.")
        return
    data = update_ticker(ticker)
    if data:
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        save_data(df)

# Uppdatera alla bolag
def update_all():
    df = load_data()
    updated_rows = []
    for _, row in df.iterrows():
        data = update_ticker(row["Ticker"])
        if data:
            updated_rows.append(data)
    if updated_rows:
        save_data(pd.DataFrame(updated_rows))

# UI
def main():
    st.title("📈 Aktieanalys – Tillväxt och Målkurs")
    df = load_data()

    st.number_input("Tillväxt 2025 (%)", value=10.0, key="tillvaxt_2025")
    st.number_input("Tillväxt 2026 (%)", value=10.0, key="tillvaxt_2026")
    st.number_input("Tillväxt 2027 (%)", value=10.0, key="tillvaxt_2027")

    new_ticker = st.text_input("Lägg till ny ticker")
    if st.button("➕ Lägg till"):
        add_ticker(new_ticker.strip().upper())

    if st.button("🔄 Uppdatera alla bolag"):
        update_all()

    if not df.empty:
        st.dataframe(df)

if __name__ == "__main__":
    main()
