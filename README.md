# Automatisk aktieanalysapp

Denna Streamlit-app gör automatiserad analys av aktier via P/S och tillväxt. Datan hämtas via Yahoo Finance och sparas i Google Sheets.

## Funktioner:
- Lägg till nya bolag
- Automatisk beräkning av P/S TTM och målkurs 2027
- Visa och ta bort bolag
- Uppdatera alla data med ett klick

## Kör lokalt
```bash
pip install -r requirements.txt
streamlit run app.py
