import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Autentisering till Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# --- Inställningar för Google Sheet ---
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = client.open_by_key(SHEET_ID)

# --- Skapa blad och rubriker om de inte finns ---
try:
    worksheet = sh.worksheet(SHEET_NAME)
except gspread.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_NAME, rows="100", cols="10")

# Kontroll: skapa rubriker om de saknas
if not worksheet.get_all_values():
    headers = ["Ticker", "Namn", "Valuta", "Senaste kurs", "Omsättning TTM", "Börsvärde",
               "Antal aktier", "P/S 1", "P/S 2", "P/S 3", "P/S 4", "P/S 5", "P/S snitt",
               "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)",
               "Omsättning 2027", "Målkurs 2027"]
    worksheet.append_row(headers)

# --- Funktion: Läs data från sheet ---
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    st.write("🔍 Kolumner i datan:", df.columns.tolist())  # felsökningsrad
    return df

# --- Funktion: Lägg till ticker om den inte redan finns ---
def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        st.error("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return
    if ticker.upper() in df["Ticker"].values:
        st.warning("⚠️ Ticker finns redan.")
    else:
        worksheet.append_row([ticker.upper()] + [""] * (len(df.columns)-1))
        st.success(f"✅ Ticker '{ticker.upper()}' tillagd!")

# --- Hämta och uppdatera info för alla tickers ---
def update_all_data():
    df = load_data()
    updated_rows = []
    for ticker in df["Ticker"]:
        try:
            info = yf.Ticker(ticker).info
            name = info.get("shortName", "")
            currency = info.get("currency", "")
            price = info.get("currentPrice", "")
            shares = info.get("sharesOutstanding", None)
            market_cap = info.get("marketCap", None)
            revenue = info.get("totalRevenue", None)

            if shares and revenue:
                ps_list = []
                for _ in range(5):
                    ps = round(market_cap / revenue, 2)
                    ps_list.append(ps)
                ps_avg = round(sum(ps_list) / len(ps_list), 2)

                # Tillväxt manuellt
                growth_2025 = 10
                growth_2026 = 10
                growth_2027 = 10
                revenue_2027 = revenue * (1 + growth_2025/100) * (1 + growth_2026/100) * (1 + growth_2027/100)
                target_price = round((revenue_2027 / shares) * ps_avg, 2)
            else:
                ps_list = [""]*5
                ps_avg = revenue_2027 = target_price = ""

            updated_row = [ticker, name, currency, price, revenue, market_cap, shares,
                           *ps_list, ps_avg, growth_2025, growth_2026, growth_2027,
                           revenue_2027, target_price]
            updated_rows.append(updated_row)
        except Exception as e:
            st.error(f"Fel vid uppdatering av {ticker}: {e}")

    if updated_rows:
        worksheet.clear()
        worksheet.append_row(["Ticker", "Namn", "Valuta", "Senaste kurs", "Omsättning TTM", "Börsvärde",
                              "Antal aktier", "P/S 1", "P/S 2", "P/S 3", "P/S 4", "P/S 5", "P/S snitt",
                              "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)",
                              "Omsättning 2027", "Målkurs 2027"])
        for row in updated_rows:
            worksheet.append_row(row)
        st.success("✅ Alla bolag uppdaterade.")

# --- Streamlit-gränssnitt ---
st.title("📈 Automatisk analys av tillväxtaktier")
new_ticker = st.text_input("Lägg till en ny ticker (t.ex. AAPL):")
if st.button("➕ Lägg till"):
    if new_ticker:
        add_ticker(new_ticker)
    else:
        st.warning("Ange en giltig ticker.")

if st.button("🔁 Uppdatera all data"):
    update_all_data()

# Visa datan
df = load_data()
if not df.empty:
    st.dataframe(df)
else:
    st.info("Inga bolag inlagda ännu.")
