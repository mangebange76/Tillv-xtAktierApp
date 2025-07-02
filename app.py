import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import numpy as np

st.set_page_config(page_title="Aktieanalys", layout="wide")

# --- Autentisering ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# --- Sheet-inställningar ---
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# --- Säkerställ rubriker finns ---
def ensure_header():
    expected = ["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM",
                "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"]
    current = worksheet.row_values(1)
    if current != expected:
        worksheet.update("A1", [expected])

# --- Ladda data ---
def load_data():
    ensure_header()
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# --- Spara data ---
def save_data(df):
    worksheet.clear()
    worksheet.update("A1", [df.columns.tolist()])
    worksheet.update("A2", df.astype(str).values.tolist())

# --- Lägg till ticker ---
def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return

    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return

    try:
        info = yf.Ticker(ticker).info
        name = info.get("shortName", "")
        price = info.get("currentPrice", np.nan)
        currency = info.get("currency", "")
        shares_outstanding = info.get("sharesOutstanding", None)

        if shares_outstanding is None or np.isnan(price):
            st.error(f"❌ Kunde inte hämta data för {ticker}")
            return

        # Omsättning TTM via kvartal
        ticker_obj = yf.Ticker(ticker)
        try:
            revs = ticker_obj.quarterly_financials.loc["Total Revenue"]
            oms_ttm = revs.iloc[:4].sum()
        except:
            oms_ttm = None

        ps_ttm = round((price * shares_outstanding) / oms_ttm, 2) if oms_ttm else None

        tillv_25 = 0
        tillv_26 = 0
        tillv_27 = 0
        oms_2027 = None
        malkurs_2027 = None

        new_row = {
            "Ticker": ticker,
            "Namn": name,
            "Nuvarande kurs": price,
            "Valuta": currency,
            "Omsättning TTM": oms_ttm,
            "P/S TTM": ps_ttm,
            "Tillväxt 2025": tillv_25,
            "Tillväxt 2026": tillv_26,
            "Tillväxt 2027": tillv_27,
            "Omsättning 2027": oms_2027,
            "Målkurs 2027": malkurs_2027,
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success(f"{ticker} tillagd.")
        st.session_state["update"] = True

    except Exception as e:
        st.error(f"❌ Fel vid tillägg: {e}")

# --- Uppdatera befintliga tickers ---
def update_all():
    df = load_data()
    updated = False

    for idx, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice", np.nan)
            currency = info.get("currency", "")
            shares_outstanding = info.get("sharesOutstanding", None)

            if shares_outstanding is None or np.isnan(price):
                continue

            # Hämta kvartalsvis omsättning
            ticker_obj = yf.Ticker(ticker)
            try:
                revs = ticker_obj.quarterly_financials.loc["Total Revenue"]
                oms_ttm = revs.iloc[:4].sum()
            except:
                oms_ttm = None

            ps_ttm = round((price * shares_outstanding) / oms_ttm, 2) if oms_ttm else None

            # Tillväxt
            g25 = float(row["Tillväxt 2025"])
            g26 = float(row["Tillväxt 2026"])
            g27 = float(row["Tillväxt 2027"])

            oms_2027 = round(oms_ttm * (1 + g25 / 100) * (1 + g26 / 100) * (1 + g27 / 100), 2) if oms_ttm else None
            malkurs = round((oms_2027 / shares_outstanding) * ps_ttm, 2) if oms_2027 and shares_outstanding and ps_ttm else None

            df.at[idx, "Nuvarande kurs"] = price
            df.at[idx, "Valuta"] = currency
            df.at[idx, "Omsättning TTM"] = oms_ttm
            df.at[idx, "P/S TTM"] = ps_ttm
            df.at[idx, "Omsättning 2027"] = oms_2027
            df.at[idx, "Målkurs 2027"] = malkurs

            updated = True
        except Exception as e:
            st.warning(f"❌ Fel vid uppdatering av {ticker}: {e}")

    if updated:
        save_data(df)
        st.success("✅ Uppdatering klar.")

# --- Gränssnitt ---
def main():
    st.title("📈 Aktieanalys 2027")

    if "page" not in st.session_state:
        st.session_state.page = 0

    df = load_data()

    # Lägg till ticker
    with st.form("Lägg till"):
        new_ticker = st.text_input("Lägg till ticker (t.ex. AAPL)").strip().upper()
        submitted = st.form_submit_button("➕ Lägg till")
        if submitted and new_ticker:
            add_ticker(new_ticker)

    # Uppdatera alla
    if st.button("🔄 Uppdatera alla"):
        update_all()
        st.session_state["update"] = True

    # Bläddringsfunktion
    if not df.empty:
        st.subheader("🔍 Analys")
        df_sorted = df.copy()
        df_sorted["Undervärdering"] = (df_sorted["Målkurs 2027"] - df_sorted["Nuvarande kurs"]) / df_sorted["Nuvarande kurs"] * 100
        df_sorted = df_sorted.sort_values(by="Undervärdering", ascending=False)

        max_page = len(df_sorted) - 1
        st.session_state.page = max(0, min(st.session_state.page, max_page))

        col1, col2, col3 = st.columns([1, 5, 1])
        with col1:
            if st.button("⬅️"):
                st.session_state.page = max(0, st.session_state.page - 1)
        with col3:
            if st.button("➡️"):
                st.session_state.page = min(max_page, st.session_state.page + 1)

        selected = df_sorted.iloc[st.session_state.page]
        st.metric("Ticker", selected["Ticker"])
        st.write(selected.to_frame().T)

if __name__ == "__main__":
    main()
