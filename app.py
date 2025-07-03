import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets setup
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

SHEET_NAME = "Aktieanalys"
WORKSHEET_NAME = "Blad1"
SPREADSHEET = client.open(SHEET_NAME)
SHEET = SPREADSHEET.worksheet(WORKSHEET_NAME)

HEADERS = [
    "Ticker", "Namn", "Valuta", "Senaste kurs", "Börsvärde", "Antal aktier", "Omsättning TTM",
    "P/S Q1", "P/S Q2", "P/S Q3", "P/S Q4", "P/S Snitt", "Tillväxt 2025 (%)",
    "Tillväxt 2026 (%)", "Tillväxt 2027 (%)", "Omsättning 2027", "Målkurs 2027"
]

def ensure_headers():
    if SHEET.row_count < 1 or SHEET.row_values(1) != HEADERS:
        SHEET.clear()
        SHEET.insert_row(HEADERS, 1)

@st.cache_data(ttl=60)
def load_data():
    ensure_headers()
    data = SHEET.get_all_records()
    return pd.DataFrame(data)

def add_ticker(ticker, tillv_2027):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("Kolumnen 'Ticker' saknas i datan.")
        return
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        namn = info.get("shortName", "")
        valuta = info.get("currency", "")
        pris = info.get("currentPrice", 0)
        marketcap = info.get("marketCap", 0)
        shares = info.get("sharesOutstanding", 0)

        q = stock.quarterly_income_stmt.loc["Total Revenue"]
        q = q.sort_index(ascending=False)
        oms_q = q.values[:4]
        oms_ttm = oms_q.sum()

        ps_list = []
        for i in range(4):
            if oms_q[i] > 0:
                ps = marketcap / oms_q[i]
                ps_list.append(round(ps, 2))
            else:
                ps_list.append(None)

        ps_snitt = round(sum([x for x in ps_list if x]) / len([x for x in ps_list if x]), 2) if any(ps_list) else None

        tillv_2025 = info.get("earningsGrowth", 0.0) * 100
        tillv_2026 = tillv_2025  # Placeholder
        tillv_2027 = float(tillv_2027)

        tillv_faktor = (1 + tillv_2025 / 100) * (1 + tillv_2026 / 100) * (1 + tillv_2027 / 100)
        oms_2027 = oms_ttm * tillv_faktor if oms_ttm else None
        malkurs = (oms_2027 / shares) * ps_snitt if oms_2027 and shares and ps_snitt else None

        row = [
            ticker, namn, valuta, pris, marketcap, shares, oms_ttm,
            *ps_list, ps_snitt, tillv_2025, tillv_2026, tillv_2027, oms_2027, malkurs
        ]
        SHEET.append_row(row)
        st.success(f"{ticker} tillagd.")
    except Exception as e:
        st.error(f"Kunde inte lägga till {ticker}: {e}")

def delete_ticker(ticker):
    df = load_data()
    for i, row in df.iterrows():
        if row["Ticker"] == ticker:
            SHEET.delete_rows(i + 2)
            st.success(f"{ticker} borttagen.")
            return
    st.warning(f"{ticker} hittades inte.")

# Streamlit UI
st.title("📈 Aktieanalys – Målkurs 2027")

df = load_data()

if df.empty or "Ticker" not in df.columns:
    st.info("Inga bolag tillagda ännu.")
else:
    current_idx = st.session_state.get("idx", 0)
    if current_idx >= len(df):
        current_idx = 0

    bolag = df.iloc[current_idx]
    st.subheader(f"{bolag['Namn']} ({bolag['Ticker']})")
    st.metric("Senaste kurs", f"{bolag['Senaste kurs']} {bolag['Valuta']}")
    st.metric("Målkurs 2027", f"{round(bolag['Målkurs 2027'],2)} {bolag['Valuta']}")
    if bolag["Målkurs 2027"] and bolag["Senaste kurs"]:
        diff = ((bolag["Målkurs 2027"] - bolag["Senaste kurs"]) / bolag["Senaste kurs"]) * 100
        st.metric("Uppsidepotential", f"{diff:.1f} %")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Föregående"):
        st.session_state.idx = max(0, current_idx - 1)
    if col2.button("➡️ Nästa"):
        st.session_state.idx = min(len(df) - 1, current_idx + 1)

st.divider()
st.subheader("➕ Lägg till nytt bolag")

new_ticker = st.text_input("Ticker (t.ex. AAPL)")
tillv = st.number_input("Förväntad tillväxt 2027 (%)", value=30.0)

if st.button("Lägg till bolag"):
    add_ticker(new_ticker.upper(), tillv)
    st.session_state.idx = 0

st.divider()
st.subheader("🗑️ Ta bort bolag")
if not df.empty and "Ticker" in df.columns:
    ticker_to_delete = st.selectbox("Välj bolag att ta bort", df["Ticker"])
    if st.button("Ta bort"):
        delete_ticker(ticker_to_delete)
        st.session_state.idx = 0
