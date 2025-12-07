# INE5454 - Gerência de Dados
## Web Scraper para Coleta de Dados de PS5

Este projeto implementa um web scraper para coletar dados de produtos PS5 de diversos sites de comércio eletrônico brasileiros.

### Sites Monitorados
- MercadoLivre (https://lista.mercadolivre.com.br/ps5)
- Kabum (https://www.kabum.com.br/gamer/playstation/consoles-playstation/playstation-5)
- Magazine Luiza (https://www.magazineluiza.com.br/busca/ps5/)
- Amazon Brasil (https://www.amazon.com.br/s?k=ps5)
- Casas Bahia (https://www.casasbahia.com.br/ps5/b)

### Dados Coletados
Cada produto coletado contém os seguintes atributos:
- **preco_vista**: Preço à vista do produto
- **preco_parcelado**: Preço parcelado (quando disponível)
- **modelo**: Modelo do PS5 (Standard, Digital Edition, Slim)
- **nome_anuncio**: Nome/título do anúncio
- **link_pagina**: URL da página do produto
- **tipo**: Tipo do produto (Console)
- **cor**: Cor do produto
- **com_leitor_disco**: Se possui leitor de disco (Sim/Não)
- **espaco_armazenamento**: Capacidade de armazenamento
- **jogos_incluidos**: Jogos incluídos no pacote
- **inclui_controles**: Se inclui controles (Sim/Não)
- **marca**: Marca do produto (Sony)

### Instalação e Execução

#### 1. Teste do Ambiente
```bash
# Verifica se todas as dependências estão funcionando
python3 test_environment.py
```

#### 2. Instalação das Dependências
```bash
# Instalar dependências Python
pip install -r requirements.txt

# Instalar Chrome e ChromeDriver (Ubuntu/Debian)
sudo apt update
sudo apt install google-chrome-stable
wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/140.0.7339.207/linux64/chromedriver-linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
sudo ln -sf /usr/local/bin/chromedriver /usr/bin/chromedriver
```

#### 3. Execução do Scraper
```bash
# Executar scraper completo (usa padrão de 50 páginas por site)
python3 ps5_scraper.py

# Executar com limite personalizado de páginas por site
export MAX_PAGES_PER_SITE=10
python3 ps5_scraper.py

# Ou definir inline
MAX_PAGES_PER_SITE=5 python3 ps5_scraper.py
```

#### 4. Configuração de Variáveis de Ambiente

O scraper suporta as seguintes variáveis de ambiente:

- **MAX_PAGES_PER_SITE**: Define o número máximo de páginas a coletar por site (padrão: 50)
  ```bash
  export MAX_PAGES_PER_SITE=10  # Coleta no máximo 10 páginas por site
  python3 ps5_scraper.py
  ```

### Arquivos do Projeto

#### Scripts Principais
- `ps5_scraper.py` - Scraper principal com todas as funcionalidades
- `test_environment.py` - Teste do ambiente e dependências
- `demo.py` - Demonstração com um site

#### Arquivos de Configuração
- `requirements.txt` - Dependências Python
- `config.py` - Configurações personalizáveis
- `install_and_run.sh` - Script de instalação automática

#### Saídas Geradas
- `ps5_products.json` - Dados em formato JSON
- `ps5_products.xlsx` - Dados em formato Excel
- `scraper.log` - Log detalhado da execução

### Funcionalidades

- ✅ Coleta configurável de páginas por site (via variável de ambiente MAX_PAGES_PER_SITE, padrão: 50)
- ✅ Remoção de duplicatas
- ✅ Tratamento robusto de erros
- ✅ Delays aleatórios para evitar bloqueios
- ✅ Logging detalhado com emojis
- ✅ Saída em JSON e Excel
- ✅ Estatísticas detalhadas
- ✅ Configurações personalizáveis

### Dependências
- Python 3.7+
- requests
- beautifulsoup4
- selenium
- lxml
- fake-useragent
- pandas
- openpyxl
- Google Chrome + ChromeDriver

### Solução de Problemas

#### Chrome não encontrado
```bash
sudo apt update
sudo apt install google-chrome-stable
```

#### ChromeDriver não encontrado
```bash
wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/140.0.7339.207/linux64/chromedriver-linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

#### Dependências Python
```bash
pip install -r requirements.txt
```

#### Teste do ambiente
```bash
python3 test_environment.py
```

### Exemplo de Uso

```bash
# 1. Testar ambiente
python3 test_environment.py

# 2. Executar scraper
python3 ps5_scraper.py

# 3. Verificar resultados
ls -la *.json *.xlsx *.log
```

### Resultados Esperados

O scraper irá gerar:
- **ps5_products.json**: Dados estruturados em JSON
- **ps5_products.xlsx**: Planilha Excel para análise
- **scraper.log**: Log detalhado da execução
- **Estatísticas**: Resumo dos dados coletados

### Observações
- O scraper inclui delays aleatórios entre requisições para evitar bloqueios
- Remove duplicatas baseado no link do produto
- Coleta dados de múltiplas páginas de cada site
- Inclui tratamento de erros robusto e retry automático
- Gera logs detalhados para debugging
- Suporta saída em JSON e Excel
- Inclui estatísticas detalhadas dos dados coletados