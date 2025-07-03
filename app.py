import streamlit as st
import pandas as pd
import gspread
import yfinance as yf
from google.oauth2.service_account import Credentials

# Autentisering med Google Sheets via secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Ange ditt kalkylarksnamn här
SHEET_NAME = "Aktieanalys"
SPREADSHEET = client.open(SHEET_NAME)
SHEET = SPREADSHEET.sheet1

# Funktion: Ladda data från Sheet
def load_data():
    try:
        data = SHEET.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")
        return pd.DataFrame()

# Funktion: Spara data till Sheet
def save_data(df):
    try:
        SHEET.clear()
        SHEET.append_row(df.columns.tolist())
        SHEET.append_rows(df.values.tolist())
    except Exception as e:
        st.error(f"Fel vid sparande till Google Sheet: {e}")

# Funktion: Hämta aktiedata och beräkna
def fetch_and_calculate(ticker, tillv_2027):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice")
        currency = info.get("currency")
        shares = info.get("sharesOutstanding")
        revenue_quarters = stock.quarterly_income_stmt.loc["Total Revenue"]
        revenue_ttm = revenue_quarters.head(4).sum()
        ps_ttm = (price * shares) / revenue_ttm if revenue_ttm else None
        tillv_2027_decimal = float(tillv_2027) / 100
        revenue_2027 = revenue_ttm * (1 + tillv_2027_decimal)
        target_price = (revenue_2027 / shares) * ps_ttm if shares and ps_ttm else None
        return {
            "Ticker": ticker,
            "Namn": info.get("shortName"),
            "Nuvarande kurs": price,
            "Valuta": currency,
            "Omsättning TTM": revenue_ttm,
            "P/S TTM": ps_ttm,
            "Tillväxt 2027": tillv_2027,
            "Omsättning 2027": revenue_2027,
            "Målkurs 2027": target_price
        }
    except Exception as e:
        st.error(f"Fel vid uppdatering av {ticker}: {e}")
        return None

# Funktion: Lägg till nytt bolag
def add_ticker(ticker, tillv_2027):
    df = load_data()
    existing = df[df["Ticker"] == ticker]
    if not existing.empty:
        st.warning("Ticker finns redan.")
        return
    result = fetch_and_calculate(ticker, tillv_2027)
    if result:
        df = pd.concat([df, pd.DataFrame([result])], ignore_index=True)
        save_data(df)
        st.success(f"{ticker} har lagts till.")

# Funktion: Uppdatera alla
def update_all():
    df = load_data()
    updated_rows = []
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        tillv_2027 = row["Tillväxt 2027"]
        updated = fetch_and_calculate(ticker, tillv_2027)
        if updated:
            updated_rows.append(updated)
    if updated_rows:
        updated_df = pd.DataFrame(updated_rows)
        save_data(updated_df)
        st.success("Alla bolag har uppdaterats.")

# Funktion: Ta bort ett bolag
def delete_ticker(ticker):
    df = load_data()
    df = df[df["Ticker"] != ticker]
    save_data(df)
    st.success(f"{ticker} har tagits bort.")

# UI
st.title("📈 Aktieanalys – Målkurs 2027")

# Nytt bolag
with st.expander("➕ Lägg till bolag"):
    new_ticker = st.text_input("Ticker (t.ex. AAPL)").upper()
    tillv = st.text_input("Förväntad tillväxt till 2027 (%)")
    if st.button("Lägg till"):
        if new_ticker and tillv:
            add_ticker(new_ticker, tillv)
        else:
            st.warning("Fyll i både ticker och tillväxt.")

# Visa data
df = load_data()
if not df.empty:
    st.dataframe(df)
    st.markdown("---")
    ticker_to_delete = st.selectbox("🗑️ Välj bolag att ta bort", df["Ticker"])
    if st.button("Ta bort valt bolag"):
        delete_ticker(ticker_to_delete)
    st.button("🔄 Uppdatera alla", on_click=update_all)
else:
    st.info("Inga bolag tillagda ännu.")
