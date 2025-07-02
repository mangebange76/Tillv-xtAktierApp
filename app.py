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

# Konfiguration
SPREADSHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sheet = client.open_by_key(SPREADSHEET_ID)
worksheet = sheet.worksheet(SHEET_NAME)

# Kolumnnamn
REQUIRED_COLUMNS = [
    "Ticker", "Namn", "Valuta", "Senaste kurs", "Antal aktier",
    "Börsvärde", "Omsättning TTM", "Tillväxt 2025 (%)", "Tillväxt 2026 (%)",
    "Tillväxt 2027 (%)", "Omsättning 2027 (beräknad)", "P/S TTM",
    "Målkurs 2027", "Uppgångspotential (%)"
]

# Ladda data
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty or any(col not in df.columns for col in REQUIRED_COLUMNS):
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return df

# Spara data
def save_data(df):
    worksheet.clear()
    worksheet.append_row(REQUIRED_COLUMNS)
    for _, row in df.iterrows():
        worksheet.append_row([row.get(col, "") for col in REQUIRED_COLUMNS])

# Lägg till ticker
def add_ticker(ticker):
    df = load_data()
    ticker = ticker.upper().strip()
    if ticker in df["Ticker"].values:
        st.warning(f"{ticker} finns redan i listan.")
        return
    try:
        info = yf.Ticker(ticker).info
        namn = info.get("shortName", "")
        valuta = info.get("currency", "")
        kurs = info.get("currentPrice", "")
        aktier = info.get("sharesOutstanding", "")
        marketcap = info.get("marketCap", "")
        revenue_ttm = info.get("totalRevenue", "")
        new_row = {
            "Ticker": ticker,
            "Namn": namn,
            "Valuta": valuta,
            "Senaste kurs": kurs,
            "Antal aktier": aktier,
            "Börsvärde": marketcap,
            "Omsättning TTM": revenue_ttm,
            "Tillväxt 2025 (%)": "",
            "Tillväxt 2026 (%)": "",
            "Tillväxt 2027 (%)": "",
            "Omsättning 2027 (beräknad)": "",
            "P/S TTM": "",
            "Målkurs 2027": "",
            "Uppgångspotential (%)": ""
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        st.success(f"{ticker} tillagt.")
    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")

# Uppdatera beräkningar
def update_all():
    df = load_data()
    for idx, row in df.iterrows():
        try:
            tillv_25 = float(row["Tillväxt 2025 (%)"])
            tillv_26 = float(row["Tillväxt 2026 (%)"])
            tillv_27 = float(row["Tillväxt 2027 (%)"])
            oms_ttm = float(row["Omsättning TTM"])
            aktier = float(row["Antal aktier"])
            kurs = float(row["Senaste kurs"])

            oms_2027 = oms_ttm * (1 + tillv_25/100) * (1 + tillv_26/100) * (1 + tillv_27/100)
            ps_ttm = row["Börsvärde"] / oms_ttm if oms_ttm else 0
            malkurs = (oms_2027 / aktier) * ps_ttm if aktier else 0
            potential = ((malkurs - kurs) / kurs * 100) if kurs else 0

            df.at[idx, "Omsättning 2027 (beräknad)"] = round(oms_2027)
            df.at[idx, "P/S TTM"] = round(ps_ttm, 2)
            df.at[idx, "Målkurs 2027"] = round(malkurs, 2)
            df.at[idx, "Uppgångspotential (%)"] = round(potential, 1)
        except Exception as e:
            st.error(f"❌ Fel vid uppdatering av {row['Ticker']}: {e}")
    save_data(df)
    st.success("✅ Alla bolag uppdaterade!")

# Ta bort ticker
def delete_ticker(ticker):
    df = load_data()
    df = df[df["Ticker"] != ticker]
    save_data(df)
    st.success(f"{ticker} borttagen.")

# Gränssnitt
def main():
    st.title("📈 Tillväxtaktier 2027")
    df = load_data()

    # Ny ticker
    new_ticker = st.text_input("Lägg till ny ticker:")
    if st.button("➕ Lägg till") and new_ticker:
        add_ticker(new_ticker)

    # Uppdatera alla
    if st.button("🔁 Uppdatera alla bolag"):
        update_all()

    # Visa bolag
    st.subheader("Analys")
    if df.empty:
        st.warning("Inga bolag ännu.")
    else:
        for idx, row in df.iterrows():
            with st.expander(f"{row['Ticker']} – {row['Namn']}"):
                st.write(f"Senaste kurs: **{row['Senaste kurs']} {row['Valuta']}**")
                st.write(f"Målkurs 2027: **{row['Målkurs 2027']} {row['Valuta']}**")
                st.write(f"Uppgångspotential: **{row['Uppgångspotential (%)']}%**")

                tillv_25 = st.number_input(
                    "Tillväxt 2025 (%)", value=float(row["Tillväxt 2025 (%)"] or 0),
                    key=f"t25_{idx}")
                tillv_26 = st.number_input(
                    "Tillväxt 2026 (%)", value=float(row["Tillväxt 2026 (%)"] or 0),
                    key=f"t26_{idx}")
                tillv_27 = st.number_input(
                    "Tillväxt 2027 (%)", value=float(row["Tillväxt 2027 (%)"] or 0),
                    key=f"t27_{idx}")

                if st.button("💾 Spara tillväxt", key=f"spara_{idx}"):
                    df.at[idx, "Tillväxt 2025 (%)"] = tillv_25
                    df.at[idx, "Tillväxt 2026 (%)"] = tillv_26
                    df.at[idx, "Tillväxt 2027 (%)"] = tillv_27
                    save_data(df)
                    st.success("Tillväxt uppdaterad.")

                if st.button("🗑️ Ta bort", key=f"del_{idx}"):
                    delete_ticker(row["Ticker"])
                    st.experimental_rerun()

if __name__ == "__main__":
    main()
