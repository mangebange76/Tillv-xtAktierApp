import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

sh = gc.open_by_key(SPREADSHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Ladda data
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or "Ticker" not in df.columns:
        return pd.DataFrame(columns=["Ticker", "Namn", "Valuta", "Nuvarande kurs", "P/S TTM", "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)", "Målkurs 2027"])
    return df

# Lägg till ticker
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    new_row = {"Ticker": ticker}
    worksheet.append_row(list(new_row.values()), value_input_option="USER_ENTERED")
    st.success(f"{ticker} tillagd!")

# Ta bort ticker
def remove_ticker(ticker):
    df = load_data()
    if ticker not in df["Ticker"].values:
        st.warning(f"{ticker} finns inte.")
        return
    index = df[df["Ticker"] == ticker].index[0]
    worksheet.delete_rows(index + 2)  # +2 p.g.a. rubrik + 0-indexering
    st.success(f"{ticker} borttagen!")

# Hämta P/S TTM
def get_ps_ttm(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.quarterly_financials.T
        if hist.empty or "Total Revenue" not in hist.columns:
            return None
        revenue_ttm = hist["Total Revenue"].head(4).sum()
        price = stock.history(period="1d")["Close"].iloc[-1]
        shares = stock.info.get("sharesOutstanding")
        if not revenue_ttm or not shares:
            return None
        market_cap = price * shares
        return market_cap / revenue_ttm
    except Exception:
        return None

# Uppdatera all data
def update_all_data():
    df = load_data()
    updated_data = []

    for index, row in df.iterrows():
        ticker = row.get("Ticker")
        if not ticker:
            continue
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice")
            currency = info.get("financialCurrency")
            name = info.get("shortName")

            ps_ttm = get_ps_ttm(ticker)
            revenue = float(info.get("totalRevenue", 0) or 0)
            shares = float(info.get("sharesOutstanding", 0) or 0)

            try:
                g25 = float(row.get("Tillväxt 2025 (%)", 0) or 0)
                g26 = float(row.get("Tillväxt 2026 (%)", 0) or 0)
                g27 = float(row.get("Tillväxt 2027 (%)", 0) or 0)
            except:
                g25 = g26 = g27 = 0

            r25 = revenue * (1 + g25 / 100)
            r26 = r25 * (1 + g26 / 100)
            r27 = r26 * (1 + g27 / 100)
            target_price = (r27 / shares) * ps_ttm if shares and ps_ttm else 0

            updated_row = {
                "Ticker": ticker,
                "Namn": name,
                "Valuta": currency,
                "Nuvarande kurs": round(price, 2) if price else None,
                "P/S TTM": round(ps_ttm, 2) if ps_ttm else None,
                "Tillväxt 2025 (%)": g25,
                "Tillväxt 2026 (%)": g26,
                "Tillväxt 2027 (%)": g27,
                "Målkurs 2027": round(target_price, 2) if target_price else None,
            }
            updated_data.append(updated_row)
        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")

    if updated_data:
        worksheet.clear()
        headers = list(updated_data[0].keys())
        worksheet.append_row(headers)
        for row in updated_data:
            worksheet.append_row(list(row.values()), value_input_option="USER_ENTERED")
        st.success("✅ Alla bolag uppdaterade!")

# Huvudgränssnitt
def main():
    st.title("📈 Tillväxtaktier – Automatisk analys")
    df = load_data()

    st.subheader("➕ Lägg till nytt bolag")
    new_ticker = st.text_input("Ange ticker (t.ex. AAPL)", key="ticker_input")
    if st.button("Lägg till"):
        add_ticker(new_ticker.upper())
        time.sleep(1)
        st.experimental_rerun()

    st.subheader("📊 Nuvarande analys")
    if df.empty:
        st.info("Inga bolag tillagda ännu.")
    else:
        sorterade = df.dropna(subset=["Nuvarande kurs", "Målkurs 2027"]).copy()
        sorterade["Uppside (%)"] = 100 * (sorterade["Målkurs 2027"] - sorterade["Nuvarande kurs"]) / sorterade["Nuvarande kurs"]
        sorterade = sorterade.sort_values(by="Uppside (%)", ascending=False).reset_index(drop=True)

        for i, row in sorterade.iterrows():
            with st.expander(f"{row['Ticker']} – {row['Namn']}"):
                st.write(f"**Nuvarande kurs**: {row['Nuvarande kurs']} {row['Valuta']}")
                st.write(f"**Målkurs 2027**: {row['Målkurs 2027']} {row['Valuta']}")
                st.write(f"**Uppside**: {round(row['Uppside (%)'], 2)}%")
                st.write(f"P/S TTM: {row['P/S TTM']}")
                st.write(f"Tillväxt 2025–2027: {row['Tillväxt 2025 (%)']}%, {row['Tillväxt 2026 (%)']}%, {row['Tillväxt 2027 (%)']}%")
                if st.button("🗑️ Ta bort", key=f"del_{i}"):
                    remove_ticker(row["Ticker"])
                    time.sleep(1)
                    st.experimental_rerun()

    st.subheader("🔁 Uppdatera data")
    if st.button("Uppdatera alla bolag"):
        update_all_data()
        time.sleep(1)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
