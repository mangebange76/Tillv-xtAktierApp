# 📈 Aktieanalys 2027

En Streamlit-app som hämtar bolagsdata via Yahoo Finance och sparar till Google Sheets.
Beräknar målkurs baserat på TTM P/S och tillväxtprognoser.

## Funktioner
- Lägg till bolag med ticker
- Automatisk hämtning av namn, kurs, omsättning, börsvärde
- Beräkning av P/S (TTM) och målkurs 2027
- Lagring i Google Sheets
- Bläddra mellan bolag
- Ta bort bolag

## Kör i Streamlit Cloud
1. Lägg in din `GOOGLE_CREDENTIALS` i `secrets.toml`
2. Anslut appen till ett offentligt Google Sheet med rätt rubriker
