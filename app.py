import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
import json
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tillväxtaktier", layout="wide")

# Autentisering till Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

@st.cache_data(ttl=60)
def load_data():
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def save_data(df):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    sheet.clear()
    sheet.insert_rows([df.columns.values.tolist()] + df.values.tolist())

def get_ps_ttm(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.quarterly_financials
        if hist.empty:
            return None, None
        revenue_quarters = stock.quarterly_financials.loc["Total Revenue"]
        ttm_revenue = revenue_quarters.head(4).sum()
        price = stock.info["currentPrice"]
        shares = stock.info.get("sharesOutstanding")
        if not shares:
            return None, None
        market_cap = price * shares
        ps_ttm = market_cap / ttm_revenue if ttm_revenue > 0 else None
        return ps_ttm, ttm_revenue
    except Exception:
        return None, None

def calculate_2027(ticker, tillv_25, tillv_26, tillv_27):
    try:
        ps_ttm, oms_ttm = get_ps_ttm(ticker)
        if not ps_ttm or not oms_ttm:
            return None, None, None
        tillv_25 = float(tillv_25) / 100
        tillv_26 = float(tillv_26) / 100
        tillv_27 = float(tillv_27) / 100
        oms_2027 = oms_ttm * (1 + tillv_25) * (1 + tillv_26) * (1 + tillv_27)
        stock = yf.Ticker(ticker)
        shares = stock.info.get("sharesOutstanding")
        if not shares:
            return None, None, None
        market_cap_2027 = oms_2027 * ps_ttm
        price_2027 = market_cap_2027 / shares
        return round(oms_2027), round(ps_ttm, 2), round(price_2027, 2)
    except Exception:
        return None, None, None

def main():
    st.title("📈 Tillväxtaktier – Målkurs 2027")
    df = load_data()

    with st.form("add_ticker_form"):
        st.subheader("Lägg till nytt bolag")
        ticker = st.text_input("Ticker (t.ex. AAPL)")
        namn = st.text_input("Namn")
        tillv_25 = st.text_input("Tillväxt 2025 (%)", "10")
        tillv_26 = st.text_input("Tillväxt 2026 (%)", "10")
        tillv_27 = st.text_input("Tillväxt 2027 (%)", "10")
        submitted = st.form_submit_button("Lägg till")

        if submitted and ticker:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                namn = namn or info.get("shortName", "")
                valuta = info.get("currency", "")
                nuvarande_kurs = info.get("currentPrice", "")
                ps_ttm, oms_ttm = get_ps_ttm(ticker)
                oms_2027, ps, mal_kurs = calculate_2027(ticker, tillv_25, tillv_26, tillv_27)

                ny_rad = {
                    "Ticker": ticker.upper(),
                    "Namn": namn,
                    "Nuvarande kurs": nuvarande_kurs,
                    "Valuta": valuta,
                    "Omsättning TTM": oms_ttm,
                    "P/S TTM": ps,
                    "Tillväxt 2025": tillv_25,
                    "Tillväxt 2026": tillv_26,
                    "Tillväxt 2027": tillv_27,
                    "Omsättning 2027": oms_2027,
                    "Målkurs 2027": mal_kurs,
                }
                df = pd.concat([df, pd.DataFrame([ny_rad])], ignore_index=True)
                save_data(df)
                st.success("✅ Bolag tillagt!")
            except Exception as e:
                st.error(f"❌ Fel vid tillägg: {e}")

    st.divider()
    st.subheader("📊 Analys")

    if df.empty:
        st.info("Inga bolag tillagda ännu.")
    else:
        for i in range(len(df)):
            rad = df.iloc[i]
            undervardering = None
            try:
                undervardering = ((rad["Målkurs 2027"] - rad["Nuvarande kurs"]) / rad["Nuvarande kurs"]) * 100
            except:
                pass
            with st.expander(f'{rad["Ticker"]} – {rad["Namn"]}', expanded=True if i == 0 else False):
                st.markdown(f'''
                **Nuvarande kurs:** {rad["Nuvarande kurs"]} {rad["Valuta"]}
                \n**P/S TTM:** {rad["P/S TTM"]}
                \n**Omsättning TTM:** {rad["Omsättning TTM"]}
                \n**Tillväxt 2025-2027:** {rad["Tillväxt 2025"]}%, {rad["Tillväxt 2026"]}%, {rad["Tillväxt 2027"]}%
                \n**Omsättning 2027:** {rad["Omsättning 2027"]}
                \n**🎯 Målkurs 2027:** {rad["Målkurs 2027"]} {rad["Valuta"]}
                \n**📉 Undervärdering:** {round(undervardering, 1)}%
                ''')

if __name__ == "__main__":
    main()
