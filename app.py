import streamlit as st
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Titel
st.set_page_config(page_title="Tillväxtaktier", layout="wide")
st.title("📈 Automatisk analys av tillväxtaktier")

# Google Sheets-autentisering
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
client = gspread.authorize(credentials)

# Ange rätt Google Sheet och blad
SPREADSHEET_NAME = "Aktieanalys"
SHEET_NAME = "Blad1"
sh = client.open(SPREADSHEET_NAME)
worksheet = sh.worksheet(SHEET_NAME)

# Hämta existerande data
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# Inmatning
st.subheader("➕ Lägg till ett nytt bolag")
with st.form("new_ticker_form"):
    ticker_input = st.text_input("Ange ticker (t.ex. AAPL eller HM-B.ST)")
    growth_2027 = st.number_input("Förväntad tillväxt 2027 (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
    submitted = st.form_submit_button("Lägg till")

    if submitted and ticker_input:
        try:
            ticker = yf.Ticker(ticker_input)
            info = ticker.info

            name = info.get("shortName", "Okänt bolag")
            currency = info.get("currency", "USD")
            price = info.get("currentPrice", None)
            shares = info.get("sharesOutstanding", None)

            if price is None or shares is None:
                st.warning("Kunde inte hämta pris eller antal aktier.")
            else:
                # Hämta kvartalsdata och beräkna TTM sales
                quarterly = ticker.quarterly_financials
                if quarterly.empty or "Total Revenue" not in quarterly.index:
                    st.warning("Kunde inte hämta omsättning.")
                else:
                    revenues = quarterly.loc["Total Revenue"].sort_index(ascending=False)
                    if len(revenues) >= 4:
                        ttm_sales = revenues.iloc[0:4].sum()
                        ps_ttm = (price * shares) / ttm_sales
                        sales_2027 = ttm_sales * (1 + growth_2027 / 100) ** 2
                        target_price = (sales_2027 / shares) * ps_ttm

                        # Lägg till till Google Sheet
                        worksheet.append_row([ticker_input, growth_2027])

                        st.success(f"{name} ({ticker_input}) har lagts till!")
                        st.info(f"Nuvarande kurs: {price:.2f} {currency}")
                        st.info(f"Beräknad målkurs 2027: {target_price:.2f} {currency}")
                    else:
                        st.warning("Inte tillräckligt med kvartalsdata.")
        except Exception as e:
            st.error(f"Fel: {e}")

# Visa nuvarande tickers
st.subheader("📋 Analyserade bolag")
if df.empty:
    st.info("Inga bolag tillagda ännu.")
else:
    for index, row in df.iterrows():
        st.markdown(f"- {row['Ticker']} – Tillväxt 2027: {row['Tillväxt 2027 (%)']}%")
