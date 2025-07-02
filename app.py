import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Autentisering via Streamlit secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
gc = gspread.authorize(credentials)

# Google Sheet ID och ark
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Tillväxtaktier"

# Hämta Google Sheet
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Funktion: Hämta befintlig data
def get_sheet_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Funktion: Spara ny rad
def add_row(ticker, tillv_2027):
    existing = worksheet.get_all_values()
    tickers = [row[0] for row in existing[1:]]
    if ticker not in tickers:
        worksheet.append_row([ticker, tillv_2027])
        st.success(f"{ticker} har lagts till!")
    else:
        st.warning(f"{ticker} finns redan.")

# Funktion: Hämta TTM-omsättning (senaste 4 kvartal)
def get_ttm_revenue(ticker_obj):
    try:
        q = ticker_obj.quarterly_financials
        revenue = q.loc["Total Revenue"].dropna()
        if len(revenue) < 4:
            return None
        return revenue.iloc[:4].sum()
    except Exception as e:
        st.session_state["log"].append(f"❌ Kunde inte hämta omsättning för {ticker_obj.ticker}: {e}")
        return None

# Funktion: Hämta antal aktier
def get_shares_outstanding(ticker_obj):
    try:
        info = ticker_obj.info
        return info.get("sharesOutstanding", None)
    except Exception as e:
        st.session_state["log"].append(f"❌ Kunde inte hämta aktier för {ticker_obj.ticker}: {e}")
        return None

# Titel
st.title("📈 Tillväxtaktier – Målkurs 2027")

# Inmatningsfält
ticker_input = st.text_input("Ange en ticker (t.ex. AAPL)")
tillv_input = st.number_input("Förväntad tillväxt till 2027 (%)", value=20)

if st.button("Lägg till bolag"):
    if ticker_input:
        add_row(ticker_input.upper(), tillv_input)
        st.experimental_rerun()

# Initiera logg
if "log" not in st.session_state:
    st.session_state["log"] = []

# Visa analys
st.subheader("🔎 Analys")
df = get_sheet_data()

results = []
for _, row in df.iterrows():
    ticker = row["Ticker"]
    tillv = row["Tillväxt 2027"]
    yf_ticker = yf.Ticker(ticker)

    try:
        price = yf_ticker.history(period="1d")["Close"].iloc[-1]
        revenue_ttm = get_ttm_revenue(yf_ticker)
        shares_out = get_shares_outstanding(yf_ticker)

        if not all([price, revenue_ttm, shares_out]):
            results.append({
                "Ticker": ticker,
                "Nuvarande kurs": "❌",
                "Omsättning TTM": revenue_ttm,
                "Antal aktier": shares_out,
                "Tillväxt %": tillv,
                "Omsättning 2027": None,
                "Målkurs 2027": "❌"
            })
            continue

        revenue_2027 = revenue_ttm * (1 + tillv / 100)
        ps_ttm = price / (revenue_ttm / shares_out)
        target_price = (revenue_2027 / shares_out) * ps_ttm

        results.append({
            "Ticker": ticker,
            "Nuvarande kurs": round(price, 2),
            "Omsättning TTM": round(revenue_ttm / 1e9, 2),
            "Antal aktier": int(shares_out),
            "Tillväxt %": tillv,
            "Omsättning 2027": round(revenue_2027 / 1e9, 2),
            "Målkurs 2027": round(target_price, 2)
        })

    except Exception as e:
        st.session_state["log"].append(f"❌ Fel för {ticker}: {e}")

# Visa tabell
if results:
    df_result = pd.DataFrame(results)
    st.dataframe(df_result)

# Logg
with st.expander("🪵 Logg för felsökning"):
    for line in st.session_state["log"]:
        st.write(line)
