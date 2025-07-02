import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# --- Autentisering och Google Sheet-setup ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Ange rätt Sheet-ID och bladnamn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Förväntade kolumnrubriker
HEADERS = [
    "Ticker", "Namn", "Valuta", "Senaste kurs", "Omsättning TTM", "Börsvärde", "Antal aktier",
    "P/S 1", "P/S 2", "P/S 3", "P/S 4", "P/S 5", "P/S snitt",
    "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)",
    "Omsättning 2027", "Målkurs 2027"
]

def initialize_headers():
    current_values = worksheet.row_values(1)
    if current_values != HEADERS:
        worksheet.clear()
        worksheet.insert_row(HEADERS, 1)

def load_data():
    initialize_headers()
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df):
    worksheet.clear()
    worksheet.insert_row(HEADERS, 1)
    if not df.empty:
        rows = df.astype(str).values.tolist()
        worksheet.append_rows(rows)

def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")
        price = hist["Close"].iloc[-1] if not hist.empty else None
        currency = info.get("currency", "")
        name = info.get("shortName", "")

        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        revenue = info.get("totalRevenue")

        if not all([price, currency, name, shares, market_cap, revenue]):
            st.warning(f"Kunde inte hämta fullständig data för {ticker}.")
            return

        # Beräkna P/S för 5 senaste kvartal
        ps_values = []
        try:
            quarters = stock.quarterly_financials.loc["Total Revenue"].sort_index(ascending=False)
            for i in range(4):
                ttm = quarters[i:i+4].sum()
                ps = market_cap / ttm if ttm != 0 else None
                if ps:
                    ps_values.append(round(ps, 2))
        except:
            pass

        ps_avg = round(sum(ps_values) / len(ps_values), 2) if ps_values else ""

        tillv_25, tillv_26, tillv_27 = "", "", ""
        oms_2027 = ""
        malkurs = ""

        new_row = [ticker, name, currency, round(price, 2), revenue, market_cap, shares] + \
                  ps_values + [""] * (5 - len(ps_values)) + [ps_avg, tillv_25, tillv_26, tillv_27, oms_2027, malkurs]

        df.loc[len(df)] = new_row
        save_data(df)
        st.success(f"{ticker} tillagd.")
    except Exception as e:
        st.error(f"Fel vid hämtning: {e}")

def main():
    st.title("📈 Aktieanalys – Målkurs via P/S TTM")

    df = load_data()

    # Tickerinmatning
    with st.form("add_ticker_form"):
        new_ticker = st.text_input("Lägg till ticker", "").upper()
        submitted = st.form_submit_button("Lägg till")
        if submitted and new_ticker:
            add_ticker(new_ticker)
            st.experimental_rerun()

    if df.empty:
        st.info("Inga aktier tillagda ännu.")
        return

    # Visa aktier
    sorterat_df = df.copy()
    if "Målkurs 2027" in sorterat_df.columns and "Senaste kurs" in sorterat_df.columns:
        try:
            sorterat_df["Undervärdering (%)"] = (
                (sorterat_df["Målkurs 2027"].astype(float) - sorterat_df["Senaste kurs"].astype(float)) /
                sorterat_df["Senaste kurs"].astype(float)
            ) * 100
            sorterat_df = sorterat_df.sort_values(by="Undervärdering (%)", ascending=False)
        except:
            pass

    st.subheader("📊 Analyserade aktier")
    st.dataframe(sorterat_df, use_container_width=True)

if __name__ == "__main__":
    main()
