mkdir -p ~/.streamlit/

echo "\
[general]
email = \"\"

[server]
headless = true
enableCORS=false
port = $PORT
" > ~/.streamlit/config.toml
