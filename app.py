import streamlit as st
import pandas as pd
import yfinance as yf
from google.oauth2.service_account import Credentials
import gspread
import datetime

st.set_page_config(page_title="Tillväxtaktier", layout="centered")

# Google Sheets-inställningar
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Skapa rubrikrad om den saknas
def ensure_headers():
    existing_data = worksheet.get_all_values()
    if not existing_data or "Ticker" not in existing_data[0]:
        headers = ["Ticker"]
        worksheet.clear()
        worksheet.append_row(headers)

# Ladda data från Google Sheet
def load_data():
    ensure_headers()
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# Lägg till ticker
def add_ticker(ticker):
    df = load_data()

    if "Ticker" not in df.columns:
        st.error("❌ Kolumnen 'Ticker' saknas i Google Sheet. Kontrollera att rad 1 innehåller 'Ticker'.")
        return

    if ticker in df["Ticker"].values:
        st.warning(f"⚠️ Ticker '{ticker}' finns redan.")
        return

    new_row = pd.DataFrame([{"Ticker": ticker}])
    df = pd.concat([df, new_row], ignore_index=True)
    worksheet.clear()
    worksheet.append_row(df.columns.tolist())
    for row in df.values.tolist():
        worksheet.append_row(row)
    st.success(f"✅ '{ticker}' har lagts till.")

# Beräkna TTM P/S-målkurs
def calculate_analysis(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.quarterly_financials
        info = ticker_data.info
        price = info.get("currentPrice")

        shares = info.get("sharesOutstanding")
        currency = info.get("currency", "USD")

        if hist.empty or not shares or not price:
            return None

        # Hämta de senaste 4 kvartalens omsättning (Revenue)
        if "Total Revenue" not in hist.index:
            return None
        revenue_q = hist.loc["Total Revenue"]
        if len(revenue_q) < 4:
            return None
        ttm_revenue = revenue_q.iloc[:4].sum()

        ps_ttm = price / (ttm_revenue / shares)
        avg_ps = round(ps_ttm, 2)
        target_price = round((ttm_revenue / shares) * avg_ps, 2)

        return {
            "Ticker": ticker,
            "Kurs": price,
            "Valuta": currency,
            "P/S TTM": avg_ps,
            "Omsättning TTM": int(ttm_revenue),
            "Målkurs": target_price,
            "Uppside (%)": round(((target_price / price) - 1) * 100, 1)
        }
    except Exception:
        return None

# Huvudfunktion
def main():
    st.title("📈 Tillväxtaktier – Automatisk analys")

    df = load_data()
    all_results = []

    for ticker in df["Ticker"]:
        result = calculate_analysis(ticker)
        if result:
            all_results.append(result)

    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df = results_df.sort_values(by="Uppside (%)", ascending=False).reset_index(drop=True)

        st.subheader("🔍 Mest undervärderade bolag")
        current_index = st.number_input("Visa bolag nummer:", min_value=1, max_value=len(results_df), value=1)
        selected = results_df.iloc[current_index - 1]

        st.markdown(f"### {selected['Ticker']}")
        st.metric("Aktuell kurs", f"{selected['Kurs']} {selected['Valuta']}")
        st.metric("P/S TTM", selected["P/S TTM"])
        st.metric("Målkurs", f"{selected['Målkurs']} {selected['Valuta']}")
        st.metric("Uppside", f"{selected['Uppside (%)']} %")
    else:
        st.info("ℹ️ Ingen komplett data kunde analyseras än. Lägg till en ticker.")

    # Lägg till ticker
    st.subheader("➕ Lägg till ny ticker")
    new_ticker = st.text_input("Ange ticker (t.ex. AAPL):").upper()
    if st.button("Lägg till"):
        if new_ticker:
            add_ticker(new_ticker)
        else:
            st.warning("⚠️ Fältet får inte vara tomt.")

if __name__ == "__main__":
    main()
