import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Inställningar
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = client.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

HEADERS = ["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"]

def ensure_headers():
    if worksheet.row_values(1) != HEADERS:
        worksheet.update("A1:K1", [HEADERS])

def load_data():
    ensure_headers()
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df):
    worksheet.clear()
    worksheet.update("A1", [HEADERS])
    if not df.empty:
        worksheet.update("A2", df.astype(str).values.tolist())

def get_ttm_revenue(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        financials = ticker_obj.quarterly_financials
        if financials.empty:
            return None
        revenue = financials.loc["Total Revenue"].dropna()
        return revenue[:4].sum()
    except:
        return None

def get_current_price_currency_name(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        return info.get("currentPrice"), info.get("currency"), info.get("shortName")
    except:
        return None, None, None

def calculate_target_price(revenue_2027, shares_outstanding):
    if shares_outstanding == 0:
        return None
    ps_target = 5
    return (revenue_2027 / shares_outstanding) * ps_target

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return

    current_price, currency, name = get_current_price_currency_name(ticker)
    ttm_revenue = get_ttm_revenue(ticker)
    if not current_price or not ttm_revenue:
        st.error("Kunde inte hämta kurs eller omsättning.")
        return

    try:
        ps_ttm = current_price / (ttm_revenue / 1_000_000_000)
    except:
        ps_ttm = None

    df = pd.concat([df, pd.DataFrame([{
        "Ticker": ticker,
        "Namn": name,
        "Nuvarande kurs": current_price,
        "Valuta": currency,
        "Omsättning TTM": ttm_revenue,
        "P/S TTM": ps_ttm,
        "Tillväxt 2025": "",
        "Tillväxt 2026": "",
        "Tillväxt 2027": "",
        "Omsättning 2027": "",
        "Målkurs 2027": ""
    }])], ignore_index=True)

    save_data(df)
    st.success(f"{ticker} har lagts till.")

def update_all_data():
    df = load_data()
    updated_rows = []
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            growth_2025 = float(row["Tillväxt 2025"])
            growth_2026 = float(row["Tillväxt 2026"])
            growth_2027 = float(row["Tillväxt 2027"])
            ttm = float(row["Omsättning TTM"])
        except:
            st.warning(f"⚠️ Hoppar över {ticker} – tillväxt eller omsättning saknas/ogiltig.")
            updated_rows.append(row)
            continue

        revenue_2027 = ttm * (1 + growth_2025 / 100) * (1 + growth_2026 / 100) * (1 + growth_2027 / 100)

        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            shares_outstanding = info.get("sharesOutstanding", 0)
        except:
            shares_outstanding = 0

        try:
            target_price = calculate_target_price(revenue_2027, shares_outstanding)
        except:
            target_price = None

        row["Omsättning 2027"] = revenue_2027
        row["Målkurs 2027"] = target_price
        updated_rows.append(row)

    save_data(pd.DataFrame(updated_rows))
    st.success("✅ Alla bolag har uppdaterats.")

def main():
    st.title("📈 Tillväxtaktier – Målkurser 2027")

    new_ticker = st.text_input("Lägg till ny ticker (t.ex. AAPL)")
    if st.button("Lägg till"):
        if new_ticker:
            add_ticker(new_ticker.strip().upper())
        else:
            st.warning("❗ Ange en giltig ticker.")

    if st.button("Uppdatera alla"):
        update_all_data()

    df = load_data()
    if not df.empty:
        st.subheader("📋 Data")
        st.dataframe(df)
    else:
        st.info("Inga tickers inlagda än.")

if __name__ == "__main__":
    main()
