import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering med Google Sheets via Streamlit secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
gc = gspread.authorize(credentials)

# Ange URL till Google Sheet
sheet_url = "https://docs.google.com/spreadsheets/d/1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo/edit#gid=0"
sheet = gc.open_by_url(sheet_url).sheet1

# Funktion: Läs data från Google Sheet
def fetch_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# Funktion: Spara ny rad till Google Sheet
def save_company(ticker, tillv_2027):
    df = fetch_data()
    if ticker in df['Ticker'].values:
        st.warning("Bolaget finns redan.")
        return

    try:
        info = yf.Ticker(ticker).info
        name = info.get("shortName", ticker)
        price = info.get("currentPrice")
        shares_out = info.get("sharesOutstanding")
        currency = info.get("financialCurrency", "USD")

        # Hämta kvartalsdata och beräkna 4 P/S TTM
        hist = yf.Ticker(ticker).quarterly_financials
        revenue_quarters = hist.loc["Total Revenue"].dropna().values[:4]
        ttm_revenue = revenue_quarters.sum()
        market_cap = price * shares_out
        ps_ttm = market_cap / ttm_revenue if ttm_revenue > 0 else None

        # Tillväxtprognos
        tillv_2027 = float(tillv_2027) / 100
        oms_2027 = ttm_revenue * (1 + tillv_2027)
        potential_price = (oms_2027 / shares_out) * ps_ttm if ps_ttm else None

        # Spara till Sheet
        new_row = [ticker, name, price, currency, ttm_revenue, shares_out, ps_ttm, tillv_2027, oms_2027, potential_price]
        sheet.append_row(new_row)
        st.success("✅ Bolaget har sparats.")
    except Exception as e:
        st.error(f"Fel vid hämtning eller beräkning: {e}")

# Funktion: Räkna om alla bolag
def update_all():
    df = fetch_data()
    sheet.clear()
    sheet.append_row(["Ticker", "Namn", "Nuvarande kurs", "Valuta", "TTM omsättning", "Antal aktier", "P/S TTM", "Tillväxt 2027", "Omsättning 2027", "Potentiell kurs 2027"])
    for _, row in df.iterrows():
        save_company(row['Ticker'], row['Tillväxt 2027'] * 100)

# Funktion: Ta bort bolag
def delete_company(ticker):
    df = fetch_data()
    index = df[df["Ticker"] == ticker].index
    if not index.empty:
        sheet.delete_rows(index[0] + 2)
        st.success("🗑️ Bolaget har tagits bort.")

# UI
st.title("📊 Automatisk analys av aktier")
tab1, tab2 = st.tabs(["➕ Lägg till bolag", "📋 Befintliga bolag"])

with tab1:
    st.subheader("Lägg till nytt bolag")
    ticker = st.text_input("Ticker (t.ex. AAPL)")
    tillv_2027 = st.number_input("Förväntad tillväxt 2027 (%)", value=10.0)

    if st.button("Lägg till"):
        if ticker and tillv_2027:
            save_company(ticker.upper(), tillv_2027)

with tab2:
    df = fetch_data()
    if not df.empty:
        df["Undervärdering (%)"] = ((df["Potentiell kurs 2027"] - df["Nuvarande kurs"]) / df["Nuvarande kurs"] * 100).round(1)
        sorted_df = df.sort_values("Undervärdering (%)", ascending=False).reset_index(drop=True)

        index = st.number_input("📉 Visa bolag", min_value=0, max_value=len(sorted_df) - 1, step=1)
        row = sorted_df.iloc[index]
        st.metric("📌 Ticker", row["Ticker"])
        st.metric("📈 Nuvarande kurs", f"{row['Nuvarande kurs']} {row['Valuta']}")
        st.metric("📊 Potentiell kurs 2027", f"{round(row['Potentiell kurs 2027'],2)} {row['Valuta']}")
        st.metric("📉 Undervärdering", f"{row['Undervärdering (%)']} %")

        if st.button("❌ Ta bort detta bolag"):
            delete_company(row["Ticker"])

    if st.button("🔄 Uppdatera alla bolag"):
        update_all()
