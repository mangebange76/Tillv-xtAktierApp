# Aktieanalysapp med Streamlit och Google Sheets

Den här appen låter dig analysera aktier baserat på tillväxt och P/S-tal. Alla bolag lagras i ett Google Sheet och du kan enkelt lägga till nya tickers, uppdatera dem och beräkna målkurs för 2027.

## Funktioner

- Lägg till aktier (via ticker)
- Hämtar automatiskt:
  - Omsättning TTM
  - Nuvarande aktiekurs
  - P/S TTM
  - Valuta
- Manuell inmatning av förväntad tillväxt för 2027
- Automatisk tillväxt för 2025–2026
- Beräknar målkurs 2027
- Sparar allt till Google Sheets
- Bläddra mellan bolag (mest undervärderad först)

## Så här kör du appen

### 1. Installera beroenden

```bash
pip install -r requirements.txt
