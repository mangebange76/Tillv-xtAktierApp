import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Google Sheet-inställningar
SHEET_NAME = "Aktieanalys"
WORKSHEET_NAME = "Blad1"
SPREADSHEET = client.open(SHEET_NAME)
SHEET = SPREADSHEET.worksheet(WORKSHEET_NAME)

# Kolumnrubriker
HEADERS = [
    "Ticker", "Namn", "Valuta", "Senaste kurs",
    "Börsvärde", "Antal aktier", "Omsättning TTM",
    "P/S Q1", "P/S Q2", "P/S Q3", "P/S Q4", "P/S Snitt",
    "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)",
    "Omsättning 2027", "Målkurs 2027"
]

# Säkerställ rubriker
def ensure_headers():
    if SHEET.row_values(1) != HEADERS:
        SHEET.update('A1', [HEADERS])

# Ladda data
def load_data():
    ensure_headers()
    data = SHEET.get_all_records()
    return pd.DataFrame(data)

# Spara ett nytt bolag
def add_ticker(ticker, tillv_2027):
    df = load_data()
    if not ticker:
        st.warning("⚠️ Ticker saknas.")
        return
    if ticker in df["Ticker"].values:
        st.warning("⚠️ Ticker finns redan.")
        return

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("longName", "")
        currency = info.get("currency", "")
        price = info.get("currentPrice", 0)
        market_cap = info.get("marketCap", 0)
        shares_out = market_cap / price if price > 0 else 0

        # Hämta kvartalsomsättning
        revs = stock.quarterly_income_stmt.loc["Total Revenue"]
        revs = revs.sort_index(ascending=False)
        if len(revs) < 4:
            st.warning("⚠️ Mindre än 4 kvartal hittades.")
            return

        ttm_revenue = revs.iloc[:4].sum()
        p_s_list = []
        for i in range(4):
            q_price = stock.history(period="1d").iloc[-1]["Close"]
            ttm = revs.iloc[i:i+4].sum()
            ps = (q_price * shares_out) / ttm if ttm > 0 else 0
            p_s_list.append(ps)

        ps_avg = sum(p_s_list) / len(p_s_list)

        # Tillväxt
        growth_2025 = info.get("earningsGrowth", 0.15) * 100
        growth_2026 = info.get("revenueGrowth", 0.12) * 100

        oms_2027 = ttm_revenue * (1 + growth_2025 / 100) * (1 + growth_2026 / 100) * (1 + tillv_2027 / 100)
        malkurs = (oms_2027 / shares_out) * ps_avg if shares_out > 0 else 0

        row = [
            ticker, name, currency, price,
            market_cap, round(shares_out), ttm_revenue,
            *[round(x, 2) for x in p_s_list], round(ps_avg, 2),
            round(growth_2025, 1), round(growth_2026, 1), tillv_2027,
            round(oms_2027), round(malkurs, 2)
        ]
        SHEET.append_row(row)
        st.success(f"✅ {ticker} tillagd!")
    except Exception as e:
        st.error(f"Något gick fel: {e}")

# Visa analys
def show_analysis():
    df = load_data()
    if df.empty:
        st.info("Ingen data än.")
        return

    df = df.sort_values("Målkurs 2027", ascending=False)
    st.dataframe(df)

    underv = df[df["Senaste kurs"] > 0].copy()
    underv["Undervärdering (%)"] = ((underv["Målkurs 2027"] - underv["Senaste kurs"]) / underv["Senaste kurs"]) * 100
    underv = underv.sort_values("Undervärdering (%)", ascending=False).reset_index(drop=True)

    index = st.number_input("📊 Visa bolag #", min_value=0, max_value=len(underv)-1, step=1)
    st.write(f"### {underv.at[index, 'Namn']} ({underv.at[index, 'Ticker']})")
    st.metric("Målkurs 2027", f"{underv.at[index, 'Målkurs 2027']:.2f} {underv.at[index, 'Valuta']}")
    st.metric("Senaste kurs", f"{underv.at[index, 'Senaste kurs']:.2f} {underv.at[index, 'Valuta']}")
    st.metric("Undervärdering", f"{underv.at[index, 'Undervärdering (%)']:.1f} %")

# Ta bort bolag
def delete_ticker():
    df = load_data()
    if df.empty:
        st.warning("Inget att ta bort.")
        return
    ticker = st.selectbox("🗑️ Välj bolag att ta bort", df["Ticker"])
    if st.button("Radera bolag"):
        all_rows = SHEET.get_all_values()
        for idx, row in enumerate(all_rows):
            if row and row[0] == ticker:
                SHEET.delete_rows(idx + 1)
                st.success(f"🗑️ {ticker} borttagen.")
                break

# Gränssnitt
st.set_page_config(page_title="Aktieanalys", layout="centered")
st.title("📈 Aktieanalys – Målkurs 2027")

with st.expander("➕ Lägg till bolag"):
    new_ticker = st.text_input("Ticker (t.ex. AAPL)")
    tillv = st.number_input("Förväntad tillväxt 2027 (%)", value=20)
    if st.button("Lägg till"):
        add_ticker(new_ticker.upper(), tillv)

show_analysis()
with st.expander("🗑️ Radera bolag"):
    delete_ticker()
