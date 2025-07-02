import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# --- Google Sheets-autentisering ---
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# --- Ange rätt Sheet-ID och namn ---
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# --- Funktion: Ladda data ---
def load_data():
    rows = worksheet.get_all_records()
    if not rows:
        return pd.DataFrame(columns=["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"])
    return pd.DataFrame(rows)

# --- Funktion: Lägg till ticker ---
def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan.")
        return
    try:
        info = yf.Ticker(ticker).info
        name = info.get("shortName", "")
        price = info.get("currentPrice", None)
        currency = info.get("currency", "")
        shares = info.get("sharesOutstanding", None)
        revenue = info.get("totalRevenue", None)

        if not all([price, shares, revenue]):
            st.error(f"❌ Kunde inte hämta fullständig data för {ticker}")
            return

        ps_ttm = round((price * shares) / revenue, 2)

        new_row = [ticker, name, price, currency, revenue, ps_ttm, "", "", "", "", ""]
        worksheet.append_row(new_row)
        st.success(f"✅ {ticker} tillagd!")
    except Exception as e:
        st.error(f"❌ Fel vid hämtning: {e}")

# --- Funktion: Uppdatera alla bolag ---
def update_all():
    df = load_data()
    updated_rows = []
    for _, row in df.iterrows():
        try:
            ticker = row["Ticker"]
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice", None)
            shares = info.get("sharesOutstanding", None)
            revenue = info.get("totalRevenue", None)
            name = info.get("shortName", "")
            currency = info.get("currency", "")
            g1 = float(row["Tillväxt 2025"]) if row["Tillväxt 2025"] else 0
            g2 = float(row["Tillväxt 2026"]) if row["Tillväxt 2026"] else 0
            g3 = float(row["Tillväxt 2027"]) if row["Tillväxt 2027"] else 0

            growth_factor = (1 + g1 / 100) * (1 + g2 / 100) * (1 + g3 / 100)
            revenue_2027 = round(revenue * growth_factor) if revenue else None
            ps = round((price * shares) / revenue, 2) if price and shares and revenue else None
            target_price = round((revenue_2027 / shares) * ps, 2) if revenue_2027 and shares and ps else ""

            updated_rows.append([ticker, name, price, currency, revenue, ps, g1, g2, g3, revenue_2027, target_price])
        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {row['Ticker']}: {e}")
            updated_rows.append(row.tolist())
    worksheet.update("A2", updated_rows)
    st.success("✅ Alla bolag uppdaterade!")

# --- Funktion: Visa bolagsinfo ---
def show_company(df):
    if df.empty:
        st.info("Inga bolag inlagda ännu.")
        return
    index = st.number_input("Bläddra bolag", min_value=0, max_value=len(df)-1, step=1)
    st.write(df.iloc[index])

# --- Streamlit-gränssnitt ---
st.title("📊 Aktieanalys med målkurs 2027")

new_ticker = st.text_input("Lägg till ticker")
if st.button("➕ Lägg till bolag") and new_ticker:
    add_ticker(new_ticker.strip().upper())

if st.button("🔄 Uppdatera alla bolag"):
    update_all()

df = load_data()
show_company(df)
