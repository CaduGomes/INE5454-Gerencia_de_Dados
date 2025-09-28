#!/usr/bin/env python3
"""
Arquivo de configuração para o scraper PS5
"""

# Configurações gerais
SCRAPER_CONFIG = {
    # Número máximo de páginas para coletar por site
    'max_pages_per_site': 8,
    
    # Delay entre requisições (em segundos)
    'min_delay': 3,
    'max_delay': 6,
    
    # Delay entre sites (em segundos)
    'min_site_delay': 5,
    'max_site_delay': 10,
    
    # Timeout para carregamento de páginas (em segundos)
    'page_timeout': 10,
    
    # Configurações do Chrome
    'chrome_options': [
        '--headless',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--window-size=1920,1080',
        '--disable-blink-features=AutomationControlled'
    ],
    
    # User agents alternativos
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
}

# URLs dos sites
SITE_URLS = {
    'mercadolivre': 'https://lista.mercadolivre.com.br/ps5',
    'kabum': 'https://www.kabum.com.br/gamer/playstation/consoles-playstation/playstation-5',
    'magazineluiza': 'https://www.magazineluiza.com.br/busca/ps5/',
    'amazon': 'https://www.amazon.com.br/s?k=ps5',
    'casasbahia': 'https://www.casasbahia.com.br/ps5/b'
}

# Seletores CSS para cada site
SITE_SELECTORS = {
    'mercadolivre': {
        'product_container': '.ui-search-item',
        'product_title': '.ui-search-item__title',
        'product_link': '.ui-search-link',
        'product_price': '.andes-money-amount__fraction',
        'product_installments': '.ui-search-price__second-line',
        'next_page': '.andes-pagination__button--next'
    },
    'kabum': {
        'product_container': '.productCard',
        'product_title': '.nameCard',
        'product_link': '.productLink',
        'product_price': '.priceCard',
        'next_page': '.nextPage'
    },
    'magazineluiza': {
        'product_container': '[data-testid="product-card"]',
        'product_title': '[data-testid="product-title"]',
        'product_link': 'a',
        'product_price': '[data-testid="price-current"]',
        'next_page': '[data-testid="pagination-next"]'
    },
    'amazon': {
        'product_container': '[data-component-type="s-search-result"]',
        'product_title': 'h2 a span',
        'product_link': 'h2 a',
        'product_price': '.a-price-whole',
        'next_page': '.s-pagination-next'
    },
    'casasbahia': {
        'product_container': '.product-item',
        'product_title': '.product-title',
        'product_link': 'a',
        'product_price': '.price',
        'next_page': '.pagination-next'
    }
}

# Padrões de extração de dados
EXTRACTION_PATTERNS = {
    'storage': [
        (r'(\d+)\s*gb', r'\1 GB'),
        (r'(\d+)\s*tb', r'\1 TB'),
        (r'(\d+)\s*terabyte', r'\1 TB'),
        (r'(\d+)\s*gigabyte', r'\1 GB'),
    ],
    'disk_reader_positive': [
        'com leitor', 'leitor de disco', 'disc version', 
        'versão com leitor', 'com disco'
    ],
    'disk_reader_negative': [
        'sem leitor', 'digital', 'digital edition', 
        'slim', 'edição digital'
    ],
    'colors': [
        'branco', 'preto', 'azul', 'vermelho', 'dourado', 
        'prata', 'cinza', 'white', 'black', 'blue', 'red'
    ],
    'controllers': [
        'controle', 'dualsense', 'joystick', 'gamepad', 'controller'
    ],
    'common_games': [
        'spider-man', 'ratchet', 'clank', 'horizon', 'forbidden west',
        'demon\'s souls', 'returnal', 'sackboy', 'astros playroom',
        'god of war', 'the last of us', 'uncharted'
    ]
}

# Configurações de saída
OUTPUT_CONFIG = {
    'json_filename': 'ps5_products.json',
    'excel_filename': 'ps5_products.xlsx',
    'log_filename': 'scraper.log',
    'encoding': 'utf-8'
}

# Configurações de logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'handlers': ['file', 'console']
}
