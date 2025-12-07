#!/bin/bash

echo "Instalando dependências do projeto PS5 Scraper..."

# Instala Python e pip se não estiverem instalados
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Cria ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instala dependências
pip install -r requirements.txt

# Instala Chrome
# O ChromeDriver será gerenciado automaticamente pelo webdriver-manager
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

echo "Instalação concluída!"
echo "Para executar o scraper, use: python3 ps5_scraper.py"
