mkdir -p ~/.streamlit/

echo "\
[general]\n\
email = \"din@email.com\"\n\
" > ~/.streamlit/credentials.toml

echo "\
[server]\n\
headless = true\n\
port = 8501\n\
enableCORS = false\n\
" > ~/.streamlit/config.toml
