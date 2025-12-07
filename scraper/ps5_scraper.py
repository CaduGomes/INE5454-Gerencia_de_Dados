#!/usr/bin/env python3
"""
Web Scraper Avançado para coleta de dados de PS5
Disciplina: INE5454 - Gerência de Dados
Versão: 2.0 - Enhanced
"""

import json
import time
import random
import re
import logging
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import pandas as pd
from datetime import datetime


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuração adicional para logs mais detalhados
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


# Configuração de variáveis de ambiente
def get_max_pages_per_site() -> int:
    """
    Retorna o número máximo de páginas a coletar por site.
    Lê da variável de ambiente MAX_PAGES_PER_SITE ou usa o valor padrão de 50.
    """
    try:
        max_pages = os.getenv('MAX_PAGES_PER_SITE', '50')
        max_pages = int(max_pages)
        if max_pages < 1:
            logger.warning(f"⚠️ MAX_PAGES_PER_SITE deve ser >= 1, usando valor padrão 50")
            return 50
        return max_pages
    except ValueError:
        logger.warning(f"⚠️ MAX_PAGES_PER_SITE inválido, usando valor padrão 50")
        return 50


@dataclass
class GameConsoleProduct:
    """Classe para representar um produto de console de vídeo game"""
    preco_vista: str = ""
    preco_parcelado: str = ""
    modelo: str = ""
    nome_anuncio: str = ""
    link_pagina: str = ""
    tipo: str = "Console"
    console_type: str = ""  # PS5, Xbox Series X, Xbox Series S, Nintendo Switch, Nintendo Switch 2
    cor: str = ""
    com_leitor_disco: str = ""
    espaco_armazenamento: str = ""
    jogos_incluidos: str = ""
    inclui_controles: str = ""
    marca: str = ""
    site_origem: str = ""
    data_coleta: str = ""
    disponibilidade: str = ""

# Alias para compatibilidade
PS5Product = GameConsoleProduct


class EnhancedBaseScraper:
    """Classe base aprimorada para todos os scrapers"""
    
    def __init__(self, site_name: str, debug_mode: bool = False):
        self.site_name = site_name
        self.debug_mode = debug_mode
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.driver = None
        
    def get_driver(self):
        """Configura e retorna o driver do Selenium com configurações otimizadas"""
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        if not self.debug_mode:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Usa webdriver-manager para gerenciar automaticamente a versão do ChromeDriver
            manager_path = ChromeDriverManager().install()
            original_path = manager_path
            logger.debug(f"🔍 Caminho retornado pelo webdriver-manager: {manager_path}")
            
            # O webdriver-manager pode retornar o caminho errado (ex: THIRD_PARTY_NOTICES.chromedriver)
            # Precisamos encontrar o executável correto no mesmo diretório ou subdiretório
            driver_path = None
            
            # Se o caminho retornado é um arquivo, verifica se é o executável correto
            if os.path.isfile(manager_path):
                # Se não é o executável, procura no mesmo diretório
                if 'THIRD_PARTY_NOTICES' in manager_path or 'LICENSE' in manager_path or manager_path.endswith('.chromedriver'):
                    driver_dir = os.path.dirname(manager_path)
                    logger.debug(f"📁 Caminho retornado não é o executável, procurando em: {driver_dir}")
                    # Procura o executável no mesmo diretório
                    possible_executable = os.path.join(driver_dir, 'chromedriver')
                    if os.path.isfile(possible_executable):
                        driver_path = possible_executable
                        logger.debug(f"✅ Encontrado executável no mesmo diretório: {driver_path}")
                else:
                    # Verifica se é realmente o executável
                    try:
                        # Tenta verificar se é um executável ELF
                        import subprocess
                        result = subprocess.run(['file', manager_path], capture_output=True, text=True, timeout=2)
                        if 'ELF' in result.stdout and 'executable' in result.stdout:
                            driver_path = manager_path
                            logger.debug(f"✅ Caminho retornado é o executável correto: {driver_path}")
                    except:
                        pass
            
            # Se ainda não encontrou, procura recursivamente
            if not driver_path:
                # Determina o diretório base para busca
                if os.path.isdir(manager_path):
                    search_dir = manager_path
                else:
                    search_dir = os.path.dirname(manager_path)
                
                logger.debug(f"🔍 Buscando executável recursivamente em: {search_dir}")
                # Procura o executável chromedriver (não arquivos .chromedriver)
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        # Procura apenas arquivos chamados 'chromedriver' sem extensão .chromedriver
                        if file == 'chromedriver' and not file.endswith('.chromedriver'):
                            full_path = os.path.join(root, file)
                            if os.path.isfile(full_path):
                                # Verifica se é um executável válido
                                try:
                                    import subprocess
                                    result = subprocess.run(['file', full_path], capture_output=True, text=True, timeout=2)
                                    if 'ELF' in result.stdout and 'executable' in result.stdout:
                                        driver_path = full_path
                                        logger.debug(f"✅ Encontrado executável válido: {driver_path}")
                                        break
                                except:
                                    # Se não conseguir verificar, assume que é o executável
                                    driver_path = full_path
                                    logger.debug(f"✅ Encontrado executável: {driver_path}")
                                    break
                    if driver_path:
                        break
            
            # Se ainda não encontrou, tenta caminhos conhecidos
            if not driver_path:
                base_dir = os.path.dirname(manager_path) if os.path.isfile(manager_path) else manager_path
                possible_paths = [
                    os.path.join(base_dir, 'chromedriver'),
                    os.path.join(base_dir, 'chromedriver-linux64', 'chromedriver'),
                    os.path.join(os.path.dirname(base_dir), 'chromedriver-linux64', 'chromedriver'),
                ]
                for path in possible_paths:
                    if os.path.isfile(path):
                        driver_path = path
                        logger.debug(f"✅ Encontrado executável em caminho conhecido: {driver_path}")
                        break
            
            # Verifica se encontrou o executável
            if not driver_path or not os.path.isfile(driver_path):
                raise FileNotFoundError(f"ChromeDriver executável não encontrado. Caminho retornado: {original_path}")
            
            # Garante que o arquivo é executável
            try:
                os.chmod(driver_path, 0o755)
                logger.debug(f"✅ Permissões de execução definidas para: {driver_path}")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível definir permissões: {e}")
            
            logger.info(f"🚀 Usando ChromeDriver em: {driver_path}")
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return self.driver
        except Exception as e:
            logger.error(f"Erro ao criar driver do Chrome: {e}")
            raise
    
    def close_driver(self):
        """Fecha o driver do Selenium"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def clean_price(self, price_text: str) -> str:
        """Limpa e formata preços"""
        if not price_text:
            return ""
        
        # Remove caracteres não numéricos exceto vírgula e ponto
        price = re.sub(r'[^\d,.]', '', price_text)
        
        # Substitui vírgula por ponto para conversão
        price = price.replace(',', '.')
        
        # Remove pontos que não sejam decimais
        if '.' in price:
            parts = price.split('.')
            if len(parts) > 2:
                price = ''.join(parts[:-1]) + '.' + parts[-1]
        
        return price
    
    def extract_storage(self, text: str) -> str:
        """Extrai informação de armazenamento do texto"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        # Padrões para diferentes capacidades
        patterns = [
            (r'(\d+)\s*gb', r'\1 GB'),
            (r'(\d+)\s*tb', r'\1 TB'),
            (r'(\d+)\s*terabyte', r'\1 TB'),
            (r'(\d+)\s*gigabyte', r'\1 GB'),
        ]
        
        for pattern, replacement in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return re.sub(pattern, replacement, text_lower)
        
        return ""
    
    def extract_disk_reader(self, text: str) -> str:
        """Extrai informação sobre leitor de disco"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['com leitor', 'leitor de disco', 'disc version', 'versão com leitor', 'com disco']):
            return "Sim"
        elif any(word in text_lower for word in ['sem leitor', 'digital', 'digital edition', 'slim', 'edição digital']):
            return "Não"
        
        return ""
    
    def extract_color(self, text: str) -> str:
        """Extrai cor do produto"""
        if not text:
            return ""
        
        text_lower = text.lower()
        colors = ['branco', 'preto', 'azul', 'vermelho', 'dourado', 'prata', 'cinza', 'white', 'black', 'blue', 'red']
        
        for color in colors:
            if color in text_lower:
                return color.capitalize()
        
        return ""
    
    def extract_controllers(self, text: str) -> str:
        """Extrai informação sobre controles incluídos"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['controle', 'dualsense', 'joystick', 'gamepad', 'controller']):
            return "Sim"
        
        return "Não"
    
    def extract_games(self, text: str) -> str:
        """Extrai jogos incluídos"""
        if not text:
            return ""
        
        text_lower = text.lower()
        games = []
        
        # Lista de jogos comuns do PS5
        common_games = [
            'spider-man', 'ratchet', 'clank', 'horizon', 'forbidden west',
            'demon\'s souls', 'returnal', 'sackboy', 'astros playroom',
            'god of war', 'the last of us', 'uncharted'
        ]
        
        for game in common_games:
            if game in text_lower:
                games.append(game.replace('\'', '').title())
        
        return ", ".join(games) if games else ""
    
    def extract_model(self, text: str) -> str:
        """Extrai modelo do console"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        # PS5
        if 'ps5' in text_lower or 'playstation 5' in text_lower or 'playstation5' in text_lower:
            if 'slim' in text_lower:
                return "PS5 Slim"
            elif 'digital' in text_lower or 'edição digital' in text_lower:
                return "PS5 Digital Edition"
            elif 'pro' in text_lower:
                return "PS5 Pro"
            else:
                return "PS5 Standard"
        # Xbox Series X
        elif 'xbox series x' in text_lower or 'xbox-series-x' in text_lower:
            return "Xbox Series X"
        # Xbox Series S
        elif 'xbox series s' in text_lower or 'xbox-series-s' in text_lower:
            return "Xbox Series S"
        # Nintendo Switch 2
        elif 'switch 2' in text_lower or 'nintendo switch 2' in text_lower:
            return "Nintendo Switch 2"
        # Nintendo Switch
        elif 'switch' in text_lower or 'nintendo switch' in text_lower:
            return "Nintendo Switch"
        
        return ""
    
    def extract_console_type(self, text: str) -> str:
        """Extrai tipo de console do texto"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        if 'ps5' in text_lower or 'playstation 5' in text_lower or 'playstation5' in text_lower:
            return "PS5"
        elif 'xbox series x' in text_lower or 'xbox-series-x' in text_lower:
            return "Xbox Series X"
        elif 'xbox series s' in text_lower or 'xbox-series-s' in text_lower:
            return "Xbox Series S"
        elif 'switch 2' in text_lower or 'nintendo switch 2' in text_lower:
            return "Nintendo Switch 2"
        elif 'switch' in text_lower or 'nintendo switch' in text_lower:
            return "Nintendo Switch"
        
        return ""
    
    def wait_and_click(self, driver, by, value, timeout=10):
        """Aguarda elemento e clica nele"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            driver.execute_script("arguments[0].click();", element)
            return True
        except TimeoutException:
            return False
    
    def safe_find_element(self, driver, by, value, timeout=5):
        """Encontra elemento de forma segura"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
    
    def safe_find_elements(self, driver, by, value, timeout=5):
        """Encontra elementos de forma segura"""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return driver.find_elements(by, value)
        except TimeoutException:
            return []
    
    def debug_page_info(self, driver, site_name):
        """Captura informações de debug da página"""
        if not self.debug_mode:
            return
            
        try:
            # Captura screenshot
            screenshot_path = f"debug_{site_name.lower().replace(' ', '_')}_screenshot.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"📸 Screenshot salvo: {screenshot_path}")
            
            # Captura HTML da página
            html_path = f"debug_{site_name.lower().replace(' ', '_')}_page.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"📄 HTML salvo: {html_path}")
            
            # Log do título da página
            page_title = driver.title
            logger.info(f"📋 Título da página: {page_title}")
            
            # Log da URL atual
            current_url = driver.current_url
            logger.info(f"🌐 URL atual: {current_url}")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao capturar debug: {e}")
    
    def log_page_elements(self, driver, selectors_to_check):
        """Loga informações sobre elementos encontrados na página"""
        logger.info(f"🔍 Verificando elementos na página...")
        
        for name, selector in selectors_to_check.items():
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"  {name}: {len(elements)} elementos encontrados")
                
                if elements and self.debug_mode:
                    # Log do primeiro elemento encontrado
                    first_element = elements[0]
                    try:
                        element_text = first_element.text[:100] + "..." if len(first_element.text) > 100 else first_element.text
                        logger.info(f"    Primeiro elemento: {element_text}")
                    except:
                        logger.info(f"    Primeiro elemento: [texto não acessível]")
                        
            except Exception as e:
                logger.warning(f"  {name}: Erro ao verificar - {e}")
    
    def wait_for_page_load(self, driver, timeout=10):
        """Aguarda a página carregar completamente"""
        try:
            # Aguarda o JavaScript carregar
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            logger.info("✅ Página carregada completamente")
            return True
        except TimeoutException:
            logger.warning("⚠️ Timeout aguardando página carregar")
            return False
    
    def extract_json_ld_products(self, driver) -> List[GameConsoleProduct]:
        """Extrai produtos de dados JSON-LD estruturados"""
        products = []
        
        try:
            # Procura por scripts com dados JSON-LD
            json_scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
            logger.info(f"🔍 Encontrados {len(json_scripts)} scripts JSON-LD")
            
            for script in json_scripts:
                try:
                    json_text = script.get_attribute('innerHTML')
                    if not json_text:
                        continue
                    
                    # Parse do JSON
                    data = json.loads(json_text)
                    
                    # Verifica se é um grafo de produtos
                    if isinstance(data, dict) and '@graph' in data:
                        products_data = data['@graph']
                    elif isinstance(data, list):
                        products_data = data
                    else:
                        continue
                    
                    logger.info(f"📦 Processando {len(products_data)} produtos do JSON-LD")
                    
                    for product_data in products_data:
                        if product_data.get('@type') == 'Product':
                            product = GameConsoleProduct()
                            product.site_origem = self.site_name
                            product.data_coleta = datetime.now().isoformat()
                            
                            # Nome do produto
                            product.nome_anuncio = product_data.get('name', '')
                            
                            # URL do produto
                            offers = product_data.get('offers', {})
                            if isinstance(offers, dict):
                                product.link_pagina = offers.get('url', '')
                                product.preco_vista = str(offers.get('price', ''))
                            
                            # Extrai informações do título
                            title_text = product.nome_anuncio.lower()
                            product.modelo = self.extract_model(title_text)
                            product.console_type = self.extract_console_type(title_text)
                            product.cor = self.extract_color(title_text)
                            product.com_leitor_disco = self.extract_disk_reader(title_text)
                            product.espaco_armazenamento = self.extract_storage(title_text)
                            product.jogos_incluidos = self.extract_games(title_text)
                            product.inclui_controles = self.extract_controllers(title_text)
                            
                            if product.nome_anuncio:  # Só adiciona se tem nome
                                products.append(product)
                                logger.debug(f"✅ Produto JSON-LD: {product.nome_anuncio[:50]}...")
                    
                except json.JSONDecodeError as e:
                    logger.debug(f"⚠️ Erro ao parsear JSON-LD: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao processar JSON-LD: {e}")
                    continue
            
            logger.info(f"📊 Total de produtos extraídos do JSON-LD: {len(products)}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair JSON-LD: {e}")
        
        return products
    
    def extract_product_urls_from_json_ld(self, driver) -> List[str]:
        """Extrai URLs dos produtos de dados JSON-LD estruturados"""
        urls = []
        
        try:
            # Procura por scripts com dados JSON-LD
            json_scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
            logger.info(f"🔍 Encontrados {len(json_scripts)} scripts JSON-LD")
            
            for script in json_scripts:
                try:
                    json_text = script.get_attribute('innerHTML')
                    if not json_text:
                        continue
                    
                    # Parse do JSON
                    data = json.loads(json_text)
                    
                    # Verifica se é um grafo de produtos
                    if isinstance(data, dict) and '@graph' in data:
                        products_data = data['@graph']
                    elif isinstance(data, list):
                        products_data = data
                    else:
                        continue
                    
                    logger.info(f"📦 Processando {len(products_data)} produtos do JSON-LD")
                    
                    for product_data in products_data:
                        if product_data.get('@type') == 'Product':
                            offers = product_data.get('offers', {})
                            if isinstance(offers, dict) and 'url' in offers:
                                url = offers['url']
                                if url and 'mercadolivre.com.br' in url:
                                    urls.append(url)
                                    logger.debug(f"🔗 URL encontrada: {url}")
                    
                except json.JSONDecodeError as e:
                    logger.debug(f"⚠️ Erro ao parsear JSON-LD: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao processar JSON-LD: {e}")
                    continue
            
            logger.info(f"📊 Total de URLs extraídas: {len(urls)}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair URLs do JSON-LD: {e}")
        
        return urls
    
    def scrape_product_page(self, driver, product_url: str) -> GameConsoleProduct:
        """Extrai dados de uma página individual de produto"""
        product = GameConsoleProduct()
        product.site_origem = self.site_name
        product.data_coleta = datetime.now().isoformat()
        product.link_pagina = product_url
        
        try:
            logger.debug(f"🔍 Acessando página do produto: {product_url}")
            driver.get(product_url)
            self.wait_for_page_load(driver)
            time.sleep(3)  # Aguarda carregar completamente
            
            # Título do produto - seletores atualizados
            title_selectors = [
                "h1.ui-pdp-title",
                ".ui-pdp-title",
                "h1[data-testid='product-title']",
                "h1",
                "[data-testid='product-title']",
                ".product-title",
                ".ui-pdp-title__label"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    product.nome_anuncio = title_elem.text.strip()
                    if product.nome_anuncio:
                        break
                except NoSuchElementException:
                    continue
            
            # Preço à vista - seletores atualizados
            price_selectors = [
                ".andes-money-amount__fraction",
                ".price-tag-fraction",
                ".ui-pdp-price__fraction",
                "[data-testid='price-current']",
                ".price-current",
                ".andes-money-amount__fraction--cents",
                ".ui-pdp-price__part--medium",
                ".andes-money-amount__fraction--cents"
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    if price_text:
                        product.preco_vista = self.clean_price(price_text)
                        break
                except NoSuchElementException:
                    continue
            
            # Preço parcelado - seletores atualizados
            installment_selectors = [
                ".ui-pdp-price__second-line",
                ".price-tag-cents",
                ".installments",
                "[data-testid='price-installments']",
                ".andes-money-amount__cents",
                ".ui-pdp-price__part--small"
            ]
            
            for selector in installment_selectors:
                try:
                    installment_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    installment_text = installment_elem.text.strip()
                    if installment_text and ("x" in installment_text.lower() or "vezes" in installment_text.lower()):
                        product.preco_parcelado = self.clean_price(installment_text)
                        break
                except NoSuchElementException:
                    continue
            
            # Descrição do produto para extrair mais informações
            description_selectors = [
                ".ui-pdp-description__content",
                ".ui-pdp-description",
                "[data-testid='product-description']",
                ".product-description"
            ]
            
            description_text = ""
            for selector in description_selectors:
                try:
                    desc_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    description_text = desc_elem.text.strip()
                    if description_text:
                        break
                except NoSuchElementException:
                    continue
            
            # Combina título e descrição para extrair informações
            full_text = f"{product.nome_anuncio} {description_text}".lower()
            
            # Extrai informações do texto combinado
            product.modelo = self.extract_model(full_text)
            product.console_type = self.extract_console_type(full_text)
            product.cor = self.extract_color(full_text)
            product.com_leitor_disco = self.extract_disk_reader(full_text)
            product.espaco_armazenamento = self.extract_storage(full_text)
            product.jogos_incluidos = self.extract_games(full_text)
            product.inclui_controles = self.extract_controllers(full_text)
            
            # Determina o tipo de console baseado na URL ou título
            if "switch" in full_text or "nintendo" in full_text:
                product.tipo = "Console Nintendo Switch"
                product.marca = "Nintendo"
            elif "xbox" in full_text:
                product.tipo = "Console Xbox"
                product.marca = "Microsoft"
            elif "playstation" in full_text or "ps5" in full_text:
                product.tipo = "Console PlayStation"
                product.marca = "Sony"
            
            # Verifica disponibilidade
            availability_selectors = [
                ".ui-pdp-stock-information__title",
                "[data-testid='availability']",
                ".availability"
            ]
            
            for selector in availability_selectors:
                try:
                    avail_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    product.disponibilidade = avail_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            logger.debug(f"✅ Produto extraído: {product.nome_anuncio[:50]}... - R$ {product.preco_vista}")
            
        except Exception as e:
            logger.debug(f"⚠️ Erro ao extrair dados da página {product_url}: {e}")
        
        return product


class MercadoLivreScraper(EnhancedBaseScraper):
    """Scraper otimizado para MercadoLivre com paginação robusta"""
    
    def __init__(self, debug_mode=False):
        super().__init__("MercadoLivre", debug_mode)
        # URLs específicas para scraping - múltiplos consoles
        self.target_urls = [
            "https://lista.mercadolivre.com.br/ps5",
            "https://lista.mercadolivre.com.br/xbox-series-x", 
            "https://lista.mercadolivre.com.br/xbox-series-s",
            "https://lista.mercadolivre.com.br/nintendo-switch",
            "https://lista.mercadolivre.com.br/nintendo-switch-2",
            "https://lista.mercadolivre.com.br/switch-2"
        ]
    
    def scrape(self) -> List[GameConsoleProduct]:
        """Executa o scraping do MercadoLivre para todas as URLs especificadas"""
        all_products = []
        
        try:
            logger.info(f"🔧 Criando driver do Chrome para {self.site_name}...")
            driver = self.get_driver()
            logger.info(f"✅ Driver criado com sucesso para {self.site_name}")
            
            # Processa cada URL especificada
            for url_index, base_url in enumerate(self.target_urls, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"🌐 PROCESSANDO URL {url_index}/{len(self.target_urls)}: {base_url}")
                logger.info(f"{'='*60}")
                
                try:
                    products = self.scrape_url_with_pagination(driver, base_url)
                    all_products.extend(products)
                    logger.info(f"✅ URL {url_index} concluída: {len(products)} produtos coletados")
                    
                    # Pausa entre URLs para evitar bloqueios
                    if url_index < len(self.target_urls):
                        pause_time = random.uniform(3, 6)
                        logger.info(f"⏳ Pausando {pause_time:.1f}s antes da próxima URL...")
                        time.sleep(pause_time)
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar URL {url_index}: {e}")
                    continue
            
            logger.info(f"🎉 Coleta do {self.site_name} concluída! Total: {len(all_products)} produtos")
            
        except Exception as e:
            logger.error(f"❌ Erro no {self.site_name}: {e}")
        finally:
            logger.info(f"🔒 Fechando driver do {self.site_name}...")
            self.close_driver()
        
        return all_products
    
    def scrape_url_with_pagination(self, driver, base_url: str) -> List[GameConsoleProduct]:
        """Scrapa uma URL específica com paginação completa"""
        products = []
        current_page = 1
        max_pages = get_max_pages_per_site()  # Lê da variável de ambiente ou usa padrão
        
        try:
            logger.info(f"🌐 Navegando para: {base_url}")
            logger.info(f"📄 Limite de páginas configurado: {max_pages}")
            driver.get(base_url)
            
            # Aguarda página carregar completamente
            logger.info(f"⏳ Aguardando página carregar...")
            self.wait_for_page_load(driver)
            time.sleep(3)
            
            # Debug: captura informações da página
            self.debug_page_info(driver, f"{self.site_name}_page_{current_page}")
            
            while current_page <= max_pages:
                logger.info(f"📄 Processando página {current_page}...")
                
                # Coleta produtos da página atual
                page_products = self._scrape_page(driver)
                products.extend(page_products)
                logger.info(f"📦 Página {current_page}: {len(page_products)} produtos coletados (Total: {len(products)})")
                
                # Verifica se há próxima página
                next_page_found = self._go_to_next_page(driver)
                
                if not next_page_found:
                    logger.info(f"✅ Última página alcançada na página {current_page}")
                    break
                
                current_page += 1
                
                # Pausa entre páginas para evitar bloqueios
                pause_time = random.uniform(2, 4)
                logger.debug(f"⏳ Pausando {pause_time:.1f}s antes da próxima página...")
                time.sleep(pause_time)
            
            logger.info(f"🎉 Coleta de {base_url} concluída: {len(products)} produtos em {current_page} páginas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar URL {base_url}: {e}")
        
        return products
    
    def _go_to_next_page(self, driver) -> bool:
        """Navega para a próxima página se disponível"""
        try:
            # Aguarda um pouco para garantir que a página carregou completamente
            time.sleep(2)
            
            # Seletores identificados: li.andes-pagination__button--next (é li, não a)
            next_page_selectors = [
                "li.andes-pagination__button--next",
                "li.andes-pagination__button--next a",
                "a[title='Seguinte']",
                ".andes-pagination__button--next",
                "a[aria-label='Seguinte']",
                ".ui-search-pagination__next",
                "a[data-testid='pagination-next']",
                "button[aria-label='Seguinte']",
                ".andes-pagination__arrow--next",
                "a[title='Próxima']",
                "a[aria-label='Próxima']",
                "button[aria-label='Próxima']"
            ]
            
            # Primeiro tenta encontrar o botão com seletores CSS
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Se for um li, tenta encontrar o link dentro dele
                    if next_button.tag_name == "li":
                        try:
                            link = next_button.find_element(By.CSS_SELECTOR, "a")
                            if link:
                                next_button = link
                        except:
                            pass
                    
                    # Verifica se o botão está habilitado e visível
                    if next_button.is_enabled() and next_button.is_displayed():
                        # Verifica se não está desabilitado
                        classes = next_button.get_attribute("class") or ""
                        if "disabled" not in classes.lower():
                            logger.info(f"🔍 Botão 'Seguinte' encontrado com seletor: {selector}")
                            
                            # Tenta clicar no botão
                            driver.execute_script("arguments[0].click();", next_button)
                            
                            # Aguarda a nova página carregar
                            self.wait_for_page_load(driver)
                            time.sleep(3)
                            
                            logger.info(f"✅ Navegou para próxima página")
                            return True
                        
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Erro com seletor {selector}: {e}")
                    continue
            
            # Se não encontrou com CSS, tenta com XPath
            xpath_selectors = [
                "//li[contains(@class, 'andes-pagination__button--next')]//a",
                "//a[contains(text(), 'Seguinte')]",
                "//button[contains(text(), 'Seguinte')]",
                "//a[contains(text(), 'Próxima')]",
                "//button[contains(text(), 'Próxima')]",
                "//a[contains(@title, 'Seguinte')]",
                "//a[contains(@aria-label, 'Seguinte')]"
            ]
            
            for xpath_selector in xpath_selectors:
                try:
                    next_button = driver.find_element(By.XPATH, xpath_selector)
                    
                    if next_button.is_enabled() and next_button.is_displayed():
                        classes = next_button.get_attribute("class") or ""
                        if "disabled" not in classes.lower():
                            logger.info(f"🔍 Botão 'Seguinte' encontrado com XPath: {xpath_selector}")
                            
                            driver.execute_script("arguments[0].click();", next_button)
                            self.wait_for_page_load(driver)
                            time.sleep(3)
                            
                            logger.info(f"✅ Navegou para próxima página")
                            return True
                            
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Erro com XPath {xpath_selector}: {e}")
                    continue
            
            logger.info(f"❌ Botão 'Seguinte' não encontrado - última página alcançada")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao navegar para próxima página: {e}")
            return False
    
    def _scrape_page(self, driver) -> List[GameConsoleProduct]:
        """Scrapa uma página específica usando seletores identificados"""
        products = []
        
        try:
            logger.info(f"🔍 Procurando por itens na página...")
            
            # Seletor identificado: li.ui-search-layout__item
            item_selectors = [
                ".ui-search-layout__item",
                ".ui-search-item",
                ".ui-search-results__item",
                "[data-testid='product-item']",
                ".ui-search-item__wrapper"
            ]
            
            items = []
            for selector in item_selectors:
                items = self.safe_find_elements(driver, By.CSS_SELECTOR, selector)
                if items:
                    logger.info(f"📋 Encontrados {len(items)} itens usando seletor: {selector}")
                    break
            
            if not items:
                logger.warning(f"❌ Nenhum item encontrado na página")
                # Tenta extrair via JSON-LD como fallback
                logger.info(f"🔍 Tentando extração via JSON-LD...")
                return self.extract_json_ld_products(driver)
            
            # Extrai dados diretamente da listagem (mais eficiente)
            for i, item in enumerate(items, 1):
                try:
                    product = GameConsoleProduct()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Link do produto - seletores identificados
                    product_url = None
                    link_selectors = [
                        "a[href*='/p/']",
                        ".ui-search-link",
                        ".ui-search-item__title a",
                        "a[data-testid='product-link']",
                        "a"
                    ]
                    
                    for link_selector in link_selectors:
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, link_selector)
                            href = link_elem.get_attribute("href")
                            if href and "mercadolivre.com.br" in href and "/p/" in href:
                                product_url = href
                                product.link_pagina = href
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not product_url:
                        continue
                    
                    # Título - seletores identificados: h3.poly-component__title-wrapper ou a.poly-component__title
                    title = None
                    title_selectors = [
                        "h3.poly-component__title-wrapper",
                        "a.poly-component__title",
                        ".ui-search-item__title",
                        "h2",
                        "h3",
                        "[class*='title']"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, selector)
                            title_text = title_elem.text.strip()
                            if title_text and len(title_text) > 10:
                                title = title_text
                                break
                        except:
                            continue
                    
                    # Se não encontrou título, tenta do link
                    if not title:
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                            title = link_elem.text.strip()
                        except:
                            pass
                    
                    product.nome_anuncio = title or ""
                    
                    # Preço - seletor identificado: span.andes-money-amount__fraction
                    price = None
                    price_selectors = [
                        "span.andes-money-amount__fraction",
                        ".andes-money-amount__fraction",
                        ".ui-search-price__part--medium",
                        "[class*='price']",
                        "[class*='money']"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_elem = item.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and re.search(r'\d+', price_text):
                                price = price_text
                                break
                        except:
                            continue
                    
                    if price:
                        product.preco_vista = self.clean_price(price)
                    
                    # Parcelamento - seletor identificado: .ui-search-price__second-line
                    try:
                        installment_elem = item.find_element(By.CSS_SELECTOR, ".ui-search-price__second-line, .ui-search-installments")
                        installment_text = installment_elem.text.strip()
                        if installment_text:
                            product.preco_parcelado = self.clean_price(installment_text)
                    except:
                        pass
                    
                    # Extrai informações do título
                    if product.nome_anuncio:
                        title_text = product.nome_anuncio.lower()
                        product.modelo = self.extract_model(title_text)
                        product.console_type = self.extract_console_type(title_text)
                        product.cor = self.extract_color(title_text)
                        product.com_leitor_disco = self.extract_disk_reader(title_text)
                        product.espaco_armazenamento = self.extract_storage(title_text)
                        product.jogos_incluidos = self.extract_games(title_text)
                        product.inclui_controles = self.extract_controllers(title_text)
                        
                        # Determina marca e tipo
                        if "switch" in title_text or "nintendo" in title_text:
                            product.marca = "Nintendo"
                            product.tipo = "Console Nintendo Switch"
                        elif "xbox" in title_text:
                            product.marca = "Microsoft"
                            product.tipo = "Console Xbox"
                        elif "playstation" in title_text or "ps5" in title_text:
                            product.marca = "Sony"
                            product.tipo = "Console PlayStation"
                        
                        products.append(product)
                        logger.debug(f"✅ Produto {i}: {product.nome_anuncio[:50]}... - R$ {product.preco_vista}")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao processar item {i}: {e}")
                    continue
            
            logger.info(f"✅ Página processada: {len(products)} produtos coletados")
        
        except Exception as e:
            logger.error(f"❌ Erro ao scrapar página do {self.site_name}: {e}")
        
        return products


class KabumScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Kabum"""
    
    def __init__(self, debug_mode=False):
        super().__init__("Kabum", debug_mode)
        self.base_url = "https://www.kabum.com.br/gamer/playstation/consoles-playstation/playstation-5"
    
    def scrape(self) -> List[GameConsoleProduct]:
        """Executa o scraping da Kabum"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            self.wait_for_page_load(driver)
            time.sleep(3)
            
            # Debug: captura informações da página
            self.debug_page_info(driver, self.site_name)
            
            # Verifica diferentes seletores possíveis para resultados
            selectors_to_check = {
                "Cards de produtos": ".productCard",
                "Lista de produtos": ".productList",
                "Grid de produtos": ".productGrid",
                "Container de produtos": ".productContainer"
            }
            
            self.log_page_elements(driver, selectors_to_check)
            
            # Tenta diferentes seletores para encontrar resultados
            results_found = False
            for name, selector in selectors_to_check.items():
                if self.safe_find_element(driver, By.CSS_SELECTOR, selector):
                    logger.info(f"✅ Encontrados resultados usando seletor: {name}")
                    results_found = True
                    break
            
            if not results_found:
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            max_pages = get_max_pages_per_site()
            for page in range(2, max_pages + 1):
                try:
                    if self.wait_and_click(driver, By.CSS_SELECTOR, ".nextPage"):
                        time.sleep(random.uniform(3, 6))
                        products.extend(self._scrape_page(driver))
                        logger.info(f"Página {page} do {self.site_name} coletada")
                    else:
                        break
                except Exception as e:
                    logger.warning(f"Erro ao navegar para página {page} do {self.site_name}: {e}")
                    break
            
            logger.info(f"Coletados {len(products)} produtos do {self.site_name}")
            
        except Exception as e:
            logger.error(f"Erro no {self.site_name}: {e}")
        finally:
            self.close_driver()
        
        return products
    
    def _scrape_page(self, driver) -> List[GameConsoleProduct]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, ".productCard")
            
            for item in items:
                try:
                    product = GameConsoleProduct()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do produto
                    title_elem = item.find_element(By.CSS_SELECTOR, ".nameCard")
                    product.nome_anuncio = title_elem.text.strip()
                    
                    # Link
                    link_elem = item.find_element(By.CSS_SELECTOR, ".productLink")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, ".priceCard")
                        product.preco_vista = self.clean_price(price_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
                    product.console_type = self.extract_console_type(title_text)
                    product.cor = self.extract_color(title_text)
                    product.com_leitor_disco = self.extract_disk_reader(title_text)
                    product.espaco_armazenamento = self.extract_storage(title_text)
                    product.jogos_incluidos = self.extract_games(title_text)
                    product.inclui_controles = self.extract_controllers(title_text)
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.debug(f"Erro ao processar item do {self.site_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro ao scrapar página do {self.site_name}: {e}")
        
        return products


class MagazineLuizaScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Magazine Luiza"""
    
    def __init__(self, debug_mode=False):
        super().__init__("Magazine Luiza", debug_mode)
        # URLs de busca para múltiplos consoles
        self.target_urls = [
            "https://www.magazineluiza.com.br/busca/ps5/",
            "https://www.magazineluiza.com.br/busca/xbox-series-x/",
            "https://www.magazineluiza.com.br/busca/xbox-series-s/",
            "https://www.magazineluiza.com.br/busca/nintendo-switch/",
            "https://www.magazineluiza.com.br/busca/nintendo-switch-2/",
            "https://www.magazineluiza.com.br/busca/switch-2/"
        ]
    
    def scrape(self) -> List[GameConsoleProduct]:
        """Executa o scraping do Magazine Luiza para todas as URLs especificadas"""
        all_products = []
        
        try:
            logger.info(f"🔧 Criando driver do Chrome para {self.site_name}...")
            driver = self.get_driver()
            logger.info(f"✅ Driver criado com sucesso para {self.site_name}")
            
            # Processa cada URL especificada
            for url_index, base_url in enumerate(self.target_urls, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"🌐 PROCESSANDO URL {url_index}/{len(self.target_urls)}: {base_url}")
                logger.info(f"{'='*60}")
                
                try:
                    products = self.scrape_url_with_pagination(driver, base_url)
                    all_products.extend(products)
                    logger.info(f"✅ URL {url_index} concluída: {len(products)} produtos coletados")
                    
                    # Pausa entre URLs para evitar bloqueios
                    if url_index < len(self.target_urls):
                        pause_time = random.uniform(3, 6)
                        logger.info(f"⏳ Pausando {pause_time:.1f}s antes da próxima URL...")
                        time.sleep(pause_time)
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar URL {url_index}: {e}")
                    continue
            
            logger.info(f"🎉 Coleta do {self.site_name} concluída! Total: {len(all_products)} produtos")
            
        except Exception as e:
            logger.error(f"❌ Erro no {self.site_name}: {e}")
        finally:
            logger.info(f"🔒 Fechando driver do {self.site_name}...")
            self.close_driver()
        
        return all_products
    
    def scrape_url_with_pagination(self, driver, base_url: str) -> List[GameConsoleProduct]:
        """Scrapa uma URL específica com paginação completa"""
        products = []
        current_page = 1
        max_pages = get_max_pages_per_site()  # Lê da variável de ambiente ou usa padrão
        
        try:
            logger.info(f"🌐 Navegando para: {base_url}")
            logger.info(f"📄 Limite de páginas configurado: {max_pages}")
            driver.get(base_url)
            
            # Aguarda página carregar completamente
            logger.info(f"⏳ Aguardando página carregar...")
            self.wait_for_page_load(driver)
            time.sleep(3)
            
            # Debug: captura informações da página
            self.debug_page_info(driver, f"{self.site_name}_page_{current_page}")
            
            while current_page <= max_pages:
                logger.info(f"📄 Processando página {current_page}...")
                
                # Coleta produtos da página atual
                page_products = self._scrape_page(driver)
                products.extend(page_products)
                logger.info(f"📦 Página {current_page}: {len(page_products)} produtos coletados (Total: {len(products)})")
                
                # Verifica se há próxima página
                next_page_found = self._go_to_next_page(driver)
                
                if not next_page_found:
                    logger.info(f"✅ Última página alcançada na página {current_page}")
                    break
                
                current_page += 1
                
                # Pausa entre páginas para evitar bloqueios
                pause_time = random.uniform(2, 4)
                logger.debug(f"⏳ Pausando {pause_time:.1f}s antes da próxima página...")
                time.sleep(pause_time)
            
            logger.info(f"🎉 Coleta de {base_url} concluída: {len(products)} produtos em {current_page} páginas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar URL {base_url}: {e}")
        
        return products
    
    def _go_to_next_page(self, driver) -> bool:
        """Navega para a próxima página se disponível"""
        try:
            # Aguarda um pouco para garantir que a página carregou completamente
            time.sleep(2)
            
            # Seletores identificados para botão de próxima página
            next_page_selectors = [
                "button[aria-label='Go to next page']",
                "button.sc-hYmls.iZjLPE",
                "button[aria-label*='next']",
                "button[aria-label*='próxima']",
                ".pagination-next",
                "[data-testid='pagination-next']"
            ]
            
            # Primeiro tenta encontrar o botão com seletores CSS
            for selector in next_page_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Verifica se o botão está habilitado e visível
                    if next_button.is_enabled() and next_button.is_displayed():
                        # Verifica se não está desabilitado
                        if "disabled" not in next_button.get_attribute("class").lower():
                            logger.info(f"🔍 Botão 'Próxima página' encontrado com seletor: {selector}")
                            
                            # Tenta clicar no botão
                            driver.execute_script("arguments[0].click();", next_button)
                            
                            # Aguarda a nova página carregar
                            self.wait_for_page_load(driver)
                            time.sleep(3)
                            
                            logger.info(f"✅ Navegou para próxima página")
                            return True
                        
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Erro com seletor {selector}: {e}")
                    continue
            
            logger.info(f"❌ Botão 'Próxima página' não encontrado - última página alcançada")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao navegar para próxima página: {e}")
            return False
    
    def _scrape_page(self, driver) -> List[GameConsoleProduct]:
        """Scrapa uma página específica usando seletores identificados"""
        products = []
        
        try:
            logger.info(f"🔍 Procurando por produtos na página...")
            
            # Seletores identificados: li contendo links com /produto/ ou /p/
            product_containers = []
            
            # Busca por todos os li que contêm links de produtos
            all_li = driver.find_elements(By.CSS_SELECTOR, "li")
            for li in all_li:
                try:
                    links = li.find_elements(By.CSS_SELECTOR, "a[href*='/produto/'], a[href*='/p/']")
                    if links:
                        product_containers.append(li)
                except:
                    continue
            
            if not product_containers:
                logger.warning(f"❌ Nenhum produto encontrado na página")
                return products
            
            logger.info(f"📋 Encontrados {len(product_containers)} produtos na página")
            
            for i, container in enumerate(product_containers, 1):
                try:
                    product = GameConsoleProduct()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Link do produto
                    link_elem = container.find_element(By.CSS_SELECTOR, "a[href*='/produto/'], a[href*='/p/']")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Título - seletores identificados
                    title = None
                    title_selectors = [
                        "h2.sc-cGNDeh.ecAzqg",
                        "h2",
                        "[class*='title']",
                        "a"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            title_elem = container.find_element(By.CSS_SELECTOR, selector)
                            title_text = title_elem.text.strip()
                            if title_text and len(title_text) > 10:
                                title = title_text
                                break
                        except:
                            continue
                    
                    if not title:
                        # Tenta pegar do link
                        try:
                            title = link_elem.text.strip()
                        except:
                            pass
                    
                    product.nome_anuncio = title or ""
                    
                    # Preço - seletores identificados
                    price = None
                    price_selectors = [
                        "p.sc-dcJsrY.lmAmKF",
                        "[class*='price']",
                        "p"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            # Verifica se contém padrão de preço
                            if "R$" in price_text or re.search(r'\d+[,.]\d{2}', price_text):
                                price = price_text
                                break
                        except:
                            continue
                    
                    if price:
                        product.preco_vista = self.clean_price(price)
                    else:
                        # Tenta buscar por regex no texto do container
                        container_text = container.text
                        price_match = re.search(r'R\$\s*[\d.,]+', container_text)
                        if price_match:
                            product.preco_vista = self.clean_price(price_match.group())
                    
                    # Extrai informações do título
                    if product.nome_anuncio:
                        title_text = product.nome_anuncio.lower()
                        product.modelo = self.extract_model(title_text)
                        product.console_type = self.extract_console_type(title_text)
                        product.cor = self.extract_color(title_text)
                        product.com_leitor_disco = self.extract_disk_reader(title_text)
                        product.espaco_armazenamento = self.extract_storage(title_text)
                        product.jogos_incluidos = self.extract_games(title_text)
                        product.inclui_controles = self.extract_controllers(title_text)
                        
                        # Determina marca e tipo
                        if "switch" in title_text or "nintendo" in title_text:
                            product.marca = "Nintendo"
                            product.tipo = "Console Nintendo Switch"
                        elif "xbox" in title_text:
                            product.marca = "Microsoft"
                            product.tipo = "Console Xbox"
                        elif "playstation" in title_text or "ps5" in title_text:
                            product.marca = "Sony"
                            product.tipo = "Console PlayStation"
                        
                        products.append(product)
                        logger.debug(f"✅ Produto {i}: {product.nome_anuncio[:50]}... - R$ {product.preco_vista}")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao processar produto {i}: {e}")
                    continue
            
            logger.info(f"✅ Página processada: {len(products)} produtos coletados")
        
        except Exception as e:
            logger.error(f"❌ Erro ao scrapar página do {self.site_name}: {e}")
        
        return products


class CasasBahiaScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Casas Bahia"""
    
    def __init__(self, debug_mode=False):
        super().__init__("Casas Bahia", debug_mode)
        self.base_url = "https://www.casasbahia.com.br/ps5/b"
    
    def scrape(self) -> List[GameConsoleProduct]:
        """Executa o scraping das Casas Bahia"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            self.wait_for_page_load(driver)
            time.sleep(3)
            
            # Debug: captura informações da página
            self.debug_page_info(driver, self.site_name)
            
            # Verifica diferentes seletores possíveis para resultados
            selectors_to_check = {
                "Títulos de produtos": "h3",
                "Cards de produtos": ".product-card",
                "Lista de produtos": ".product-list",
                "Grid de produtos": ".product-grid",
                "Itens de busca": ".search-item",
                "Produtos": ".product"
            }
            
            self.log_page_elements(driver, selectors_to_check)
            
            # Tenta diferentes seletores para encontrar resultados
            results_found = False
            for name, selector in selectors_to_check.items():
                if self.safe_find_element(driver, By.CSS_SELECTOR, selector):
                    logger.info(f"✅ Encontrados resultados usando seletor: {name}")
                    results_found = True
                    break
            
            if not results_found:
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            max_pages = get_max_pages_per_site()
            for page in range(2, max_pages + 1):
                try:
                    if self.wait_and_click(driver, By.CSS_SELECTOR, "button[aria-label='Próxima página']"):
                        time.sleep(random.uniform(3, 6))
                        products.extend(self._scrape_page(driver))
                        logger.info(f"Página {page} do {self.site_name} coletada")
                    else:
                        break
                except Exception as e:
                    logger.warning(f"Erro ao navegar para página {page} do {self.site_name}: {e}")
                    break
            
            logger.info(f"Coletados {len(products)} produtos do {self.site_name}")
            
        except Exception as e:
            logger.error(f"Erro no {self.site_name}: {e}")
        finally:
            self.close_driver()
        
        return products
    
    def _scrape_page(self, driver) -> List[GameConsoleProduct]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            # Busca por todos os headings h3 que contêm produtos
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, "h3")
            
            for item in items:
                try:
                    # Verifica se é um produto (contém link)
                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    if not link_elem:
                        continue
                        
                    product = GameConsoleProduct()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do produto (texto do heading)
                    product.nome_anuncio = item.text.strip()
                    
                    # Link
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço - busca no elemento pai (próximos elementos)
                    try:
                        # Busca o preço nos elementos seguintes
                        parent = item.find_element(By.XPATH, "./..")
                        price_text = ""
                        
                        # Tenta encontrar preço em diferentes elementos
                        price_selectors = [
                            "text[contains(., 'R$')]",
                            "paragraph[contains(., 'R$')]",
                            "text[contains(., 'por R$')]"
                        ]
                        
                        for selector in price_selectors:
                            try:
                                price_elem = parent.find_element(By.XPATH, f".//{selector}")
                                price_text = price_elem.text
                                break
                            except NoSuchElementException:
                                continue
                        
                        if price_text:
                            product.preco_vista = self.clean_price(price_text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
                    product.console_type = self.extract_console_type(title_text)
                    product.cor = self.extract_color(title_text)
                    product.com_leitor_disco = self.extract_disk_reader(title_text)
                    product.espaco_armazenamento = self.extract_storage(title_text)
                    product.jogos_incluidos = self.extract_games(title_text)
                    product.inclui_controles = self.extract_controllers(title_text)
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.debug(f"Erro ao processar item do {self.site_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro ao scrapar página do {self.site_name}: {e}")
        
        return products


def generate_statistics(products: List[GameConsoleProduct]) -> Dict:
    """Gera estatísticas dos produtos coletados"""
    stats = {
        'total_produtos': len(products),
        'por_site': {},
        'por_modelo': {},
        'com_preco': 0,
        'com_leitor_disco': 0,
        'sem_leitor_disco': 0,
        'com_controles': 0,
        'com_jogos': 0,
        'cores': {},
        'armazenamento': {}
    }
    
    for product in products:
        # Por site
        site = product.site_origem
        stats['por_site'][site] = stats['por_site'].get(site, 0) + 1
        
        # Por modelo
        modelo = product.modelo or "Não especificado"
        stats['por_modelo'][modelo] = stats['por_modelo'].get(modelo, 0) + 1
        
        # Com preço
        if product.preco_vista:
            stats['com_preco'] += 1
        
        # Leitor de disco
        if product.com_leitor_disco == "Sim":
            stats['com_leitor_disco'] += 1
        elif product.com_leitor_disco == "Não":
            stats['sem_leitor_disco'] += 1
        
        # Controles
        if product.inclui_controles == "Sim":
            stats['com_controles'] += 1
        
        # Jogos
        if product.jogos_incluidos:
            stats['com_jogos'] += 1
        
        # Cores
        if product.cor:
            stats['cores'][product.cor] = stats['cores'].get(product.cor, 0) + 1
        
        # Armazenamento
        if product.espaco_armazenamento:
            stats['armazenamento'][product.espaco_armazenamento] = stats['armazenamento'].get(product.espaco_armazenamento, 0) + 1
    
    return stats


def save_to_excel(products: List[GameConsoleProduct], filename: str = "ps5_products.xlsx"):
    """Salva os produtos em arquivo Excel"""
    try:
        df = pd.DataFrame([asdict(product) for product in products])
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Dados salvos em {filename}")
    except Exception as e:
        logger.error(f"Erro ao salvar Excel: {e}")


def main(debug_mode=False):
    """Função principal que executa os scrapers do Magazine Luiza e Mercado Livre"""
    logger.info("🎮 === INICIANDO COLETA DE DADOS DE CONSOLES ===")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Mostra configuração de páginas
    max_pages = get_max_pages_per_site()
    logger.info(f"📄 Limite máximo de páginas por site: {max_pages} (configurado via MAX_PAGES_PER_SITE)")
    
    if debug_mode:
        logger.info("🐛 MODO DEBUG ATIVADO - Screenshots e HTML serão salvos")
    
    all_products = []
    
    # Scraper do Magazine Luiza
    logger.info(f"\n{'='*60}")
    logger.info("🌐 INICIANDO COLETA DO MAGAZINE LUIZA")
    logger.info(f"{'='*60}")
    
    try:
        magalu_scraper = MagazineLuizaScraper(debug_mode)
        logger.info(f"🌐 URLs para coletar: {len(magalu_scraper.target_urls)}")
        logger.info(f"📋 URLs:")
        for i, url in enumerate(magalu_scraper.target_urls, 1):
            logger.info(f"  {i}. {url}")
        
        start_time = time.time()
        magalu_products = magalu_scraper.scrape()
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Magazine Luiza concluído em {duration:.1f}s - {len(magalu_products)} produtos coletados")
        all_products.extend(magalu_products)
        
    except Exception as e:
        logger.error(f"❌ Erro ao coletar dados do Magazine Luiza: {e}")
    
    # Pausa entre scrapers
    logger.info(f"\n⏳ Pausando 5s antes de iniciar Mercado Livre...")
    time.sleep(5)
    
    # Scraper do Mercado Livre
    logger.info(f"\n{'='*60}")
    logger.info("🌐 INICIANDO COLETA DO MERCADO LIVRE")
    logger.info(f"{'='*60}")
    
    try:
        ml_scraper = MercadoLivreScraper(debug_mode)
        logger.info(f"🌐 URLs para coletar: {len(ml_scraper.target_urls)}")
        logger.info(f"📋 URLs:")
        for i, url in enumerate(ml_scraper.target_urls, 1):
            logger.info(f"  {i}. {url}")
        
        start_time = time.time()
        ml_products = ml_scraper.scrape()
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Mercado Livre concluído em {duration:.1f}s - {len(ml_products)} produtos coletados")
        all_products.extend(ml_products)
        
    except Exception as e:
        logger.error(f"❌ Erro ao coletar dados do Mercado Livre: {e}")
    
    # Remove duplicatas baseado no link
    logger.info(f"\n{'='*50}")
    logger.info("PROCESSANDO DADOS COLETADOS")
    logger.info(f"{'='*50}")
    
    unique_products = []
    seen_links = set()
    
    for product in all_products:
        if product.link_pagina and product.link_pagina not in seen_links:
            seen_links.add(product.link_pagina)
            unique_products.append(product)
    
    logger.info(f"📊 Total de produtos únicos coletados: {len(unique_products)}")
    
    # Separa produtos por site
    magalu_products = [p for p in unique_products if p.site_origem == "Magazine Luiza"]
    ml_products = [p for p in unique_products if p.site_origem == "MercadoLivre"]
    
    # Salva produtos do Magazine Luiza
    if magalu_products:
        magalu_dict = [asdict(product) for product in magalu_products]
        magalu_file = "magazineluiza_products.json"
        with open(magalu_file, 'w', encoding='utf-8') as f:
            json.dump(magalu_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Dados do Magazine Luiza salvos em {magalu_file}")
    
    # Salva produtos do Mercado Livre
    if ml_products:
        ml_dict = [asdict(product) for product in ml_products]
        ml_file = "mercadolivre_products.json"
        with open(ml_file, 'w', encoding='utf-8') as f:
            json.dump(ml_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Dados do Mercado Livre salvos em {ml_file}")
    
    # Gera estatísticas
    stats = generate_statistics(unique_products)
    
    logger.info(f"\n{'='*50}")
    logger.info("ESTATÍSTICAS FINAIS")
    logger.info(f"{'='*50}")
    
    logger.info(f"📈 Total de produtos: {stats['total_produtos']}")
    logger.info(f"  - Magazine Luiza: {len(magalu_products)}")
    logger.info(f"  - Mercado Livre: {len(ml_products)}")
    logger.info(f"💰 Produtos com preço: {stats['com_preco']}")
    logger.info(f"💿 Com leitor de disco: {stats['com_leitor_disco']}")
    logger.info(f"📱 Sem leitor de disco: {stats['sem_leitor_disco']}")
    logger.info(f"🎮 Com controles: {stats['com_controles']}")
    logger.info(f"🎯 Com jogos: {stats['com_jogos']}")
    
    logger.info(f"\n📊 Distribuição por tipo de console:")
    console_types = {}
    for product in unique_products:
        console_type = product.console_type or "Não especificado"
        console_types[console_type] = console_types.get(console_type, 0) + 1
    
    for console_type, count in console_types.items():
        logger.info(f"  {console_type}: {count}")
    
    logger.info(f"\n📊 Distribuição por modelo:")
    for modelo, count in stats['por_modelo'].items():
        logger.info(f"  {modelo}: {count}")
    
    logger.info(f"\n🏷️ Distribuição por marca:")
    marcas = {}
    for product in unique_products:
        marca = product.marca or "Não especificada"
        marcas[marca] = marcas.get(marca, 0) + 1
    
    for marca, count in marcas.items():
        logger.info(f"  {marca}: {count}")
    
    if stats['cores']:
        logger.info(f"\n🎨 Cores encontradas:")
        for color, count in stats['cores'].items():
            logger.info(f"  {color}: {count}")
    
    if stats['armazenamento']:
        logger.info(f"\n💾 Armazenamento:")
        for storage, count in stats['armazenamento'].items():
            logger.info(f"  {storage}: {count}")
    
    logger.info(f"\n✅ COLETA CONCLUÍDA COM SUCESSO!")
    logger.info(f"📁 Arquivos gerados:")
    if magalu_products:
        logger.info(f"  - magazineluiza_products.json")
    if ml_products:
        logger.info(f"  - mercadolivre_products.json")
    logger.info(f"  - scraper.log")


if __name__ == "__main__":
    import sys
    debug_mode = "--debug" in sys.argv
    main(debug_mode)
