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

# Instala Chrome e ChromeDriver
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Instala ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

echo "Instalação concluída!"
echo "Para executar o scraper, use: python3 ps5_scraper.py"
