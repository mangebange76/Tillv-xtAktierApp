import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# 🛡️ Auktorisering för Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# 🧾 Google Sheet ID och bladnamn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

HEADERS = [
    "Ticker", "Namn", "Valuta", "Senaste kurs",
    "Market Cap", "TTM Sales", "Antal aktier",
    "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)",
    "Omsättning 2025", "Omsättning 2026", "Omsättning 2027",
    "Genomsnittligt P/S", "Målkurs 2027"
]

def load_data():
    try:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        if "Ticker" not in df.columns:
            st.warning("⛔ Sheet saknar 'Ticker'-kolumn. Skapar rubriker automatiskt...")
            worksheet.clear()
            worksheet.append_row(HEADERS)
            return pd.DataFrame(columns=HEADERS)

        return df
    except Exception as e:
        st.error(f"❌ Fel vid laddning av data: {e}")
        return pd.DataFrame(columns=HEADERS)

def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.info("Bolaget finns redan.")
        return
    worksheet.append_row([ticker] + [""] * (len(HEADERS) - 1))

def update_all_data():
    df = load_data()
    updated_rows = []

    for _, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            info = yf.Ticker(ticker).info
            hist = yf.Ticker(ticker).history(period="1y", interval="3mo")
            if hist.empty:
                continue

            ps_list = []
            for i in range(4):
                try:
                    market_cap = info.get("marketCap", 0)
                    revenue_ttm = info.get("totalRevenue", 1)
                    ps = market_cap / revenue_ttm if revenue_ttm else 0
                    ps_list.append(ps)
                except:
                    ps_list.append(0)

            ps_valid = [p for p in ps_list if p > 0]
            avg_ps = sum(ps_valid) / len(ps_valid) if ps_valid else 0

            price = info.get("currentPrice", 0)
            name = info.get("shortName", "")
            currency = info.get("financialCurrency", "")
            shares = info.get("sharesOutstanding", 0)
            revenue = info.get("totalRevenue", 0)

            g25 = row.get("Tillväxt 2025 (%)", 0)
            g26 = row.get("Tillväxt 2026 (%)", 0)
            g27 = row.get("Tillväxt 2027 (%)", 0)

            r25 = revenue * (1 + g25 / 100)
            r26 = r25 * (1 + g26 / 100)
            r27 = r26 * (1 + g27 / 100)
            target_price = (r27 / shares) * avg_ps if shares else 0

            updated_row = [
                ticker, name, currency, price, info.get("marketCap", 0),
                revenue, shares, g25, g26, g27, r25, r26, r27,
                round(avg_ps, 2), round(target_price, 2)
            ]
            updated_rows.append(updated_row)

        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")
            continue

    if updated_rows:
        worksheet.clear()
        worksheet.append_row(HEADERS)
        for row in updated_rows:
            worksheet.append_row(row)

def main():
    st.title("📈 Automatisk tillväxtanalys")
    st.write("Lägg till en ticker nedan för att hämta data från Yahoo Finance.")

    new_ticker = st.text_input("Ny ticker (t.ex. AAPL)", "")
    if st.button("Lägg till ticker"):
        if new_ticker.strip():
            add_ticker(new_ticker.strip().upper())

    if st.button("🔄 Uppdatera all data"):
        update_all_data()
        st.success("✅ Uppdatering klar!")

    df = load_data()
    if not df.empty:
        st.dataframe(df)

if __name__ == "__main__":
    main()
