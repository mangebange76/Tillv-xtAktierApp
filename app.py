import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Sheetinställningar
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sheet = client.open_by_key(SHEET_ID)
worksheet = sheet.worksheet(SHEET_NAME)

# Kolumner
HEADERS = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM",
    "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"
]

# Säkerställ rubriker
if not worksheet.get_all_values():
    worksheet.append_row(HEADERS)

def load_data():
    rows = worksheet.get_all_records()
    df = pd.DataFrame(rows)
    return df

def save_data(df):
    worksheet.clear()
    worksheet.append_row(HEADERS)
    worksheet.append_rows(df.values.tolist())

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning(f"⚠️ {ticker} finns redan.")
        return
    new_row = [ticker] + [""] * (len(HEADERS) - 1)
    df.loc[len(df)] = new_row
    save_data(df)
    st.success(f"✅ {ticker} har lagts till.")

def update_all_data():
    df = load_data()
    updated_rows = []
    for index, row in df.iterrows():
        ticker = row["Ticker"]
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName", "")
            currency = info.get("currency", "")
            price = info.get("currentPrice", None)
            shares_outstanding = info.get("sharesOutstanding", None)

            # TTM försäljning
            ttm_revenue = 0
            try:
                quarterly = stock.quarterly_financials
                if quarterly is not None and not quarterly.empty:
                    ttm_revenue = quarterly.loc["Total Revenue"].iloc[:4].sum()
            except Exception:
                pass

            if not price or not ttm_revenue or not shares_outstanding:
                raise ValueError("Ofullständig data")

            ps_ttm = round((shares_outstanding * price) / ttm_revenue, 2)

            tillv_2025 = float(row["Tillväxt 2025"]) if row["Tillväxt 2025"] else 0
            tillv_2026 = float(row["Tillväxt 2026"]) if row["Tillväxt 2026"] else 0
            tillv_2027 = float(row["Tillväxt 2027"]) if row["Tillväxt 2027"] else 0

            oms_2027 = ttm_revenue * (1 + tillv_2025 / 100) * (1 + tillv_2026 / 100) * (1 + tillv_2027 / 100)
            malkurs_2027 = round((oms_2027 / shares_outstanding) * ps_ttm, 2)

            updated_row = [
                ticker, name, price, currency, round(ttm_revenue, 2), ps_ttm,
                tillv_2025, tillv_2026, tillv_2027,
                round(oms_2027, 2), malkurs_2027
            ]
            updated_rows.append(updated_row)
        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")
            updated_rows.append(row.tolist())

    updated_df = pd.DataFrame(updated_rows, columns=HEADERS)
    save_data(updated_df)
    st.success("✅ Alla bolag uppdaterade!")

def main():
    st.title("📈 Aktieanalys: Målkurs 2027")
    df = load_data()

    new_ticker = st.text_input("Lägg till ny ticker:")
    if st.button("➕ Lägg till"):
        if new_ticker:
            add_ticker(new_ticker.strip().upper())
        else:
            st.warning("Ange en giltig ticker.")

    if st.button("🔄 Uppdatera alla bolag"):
        update_all_data()

    st.subheader("Bolag i databasen")
    st.dataframe(df)

if __name__ == "__main__":
    main()
