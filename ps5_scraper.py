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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
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


@dataclass
class PS5Product:
    """Classe para representar um produto PS5"""
    preco_vista: str = ""
    preco_parcelado: str = ""
    modelo: str = ""
    nome_anuncio: str = ""
    link_pagina: str = ""
    tipo: str = "Console"
    cor: str = ""
    com_leitor_disco: str = ""
    espaco_armazenamento: str = ""
    jogos_incluidos: str = ""
    inclui_controles: str = ""
    marca: str = "Sony"
    site_origem: str = ""
    data_coleta: str = ""
    disponibilidade: str = ""


class EnhancedBaseScraper:
    """Classe base aprimorada para todos os scrapers"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
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
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            # Usa o ChromeDriver com configurações simples
            self.driver = webdriver.Chrome(options=chrome_options)
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
        """Extrai modelo do PS5"""
        if not text:
            return ""
        
        text_lower = text.lower()
        
        if 'slim' in text_lower:
            return "PS5 Slim"
        elif 'digital' in text_lower or 'edição digital' in text_lower:
            return "PS5 Digital Edition"
        else:
            return "PS5 Standard"
    
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


class MercadoLivreScraper(EnhancedBaseScraper):
    """Scraper aprimorado para MercadoLivre"""
    
    def __init__(self):
        super().__init__("MercadoLivre")
        self.base_url = "https://lista.mercadolivre.com.br/ps5"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping do MercadoLivre"""
        products = []
        
        try:
            logger.info(f"🔧 Criando driver do Chrome para {self.site_name}...")
            driver = self.get_driver()
            logger.info(f"✅ Driver criado com sucesso para {self.site_name}")
            
            logger.info(f"🌐 Navegando para {self.base_url}...")
            driver.get(self.base_url)
            logger.info(f"⏳ Aguardando página carregar (3s)...")
            time.sleep(3)
            
            # Aguarda carregar a página
            logger.info(f"🔍 Procurando por resultados na página...")
            if not self.safe_find_element(driver, By.CSS_SELECTOR, ".ui-search-results"):
                logger.warning(f"❌ Não foi possível carregar resultados do {self.site_name}")
                return products
            
            logger.info(f"✅ Página carregada com sucesso! Iniciando coleta da página 1...")
            # Coleta produtos da primeira página
            page_products = self._scrape_page(driver)
            products.extend(page_products)
            logger.info(f"📦 Página 1: {len(page_products)} produtos coletados (Total: {len(products)})")
            
            # Tenta navegar para próximas páginas
            for page in range(2, 8):  # Aumenta para 8 páginas
                try:
                    logger.info(f"🔄 Tentando navegar para página {page}...")
                    if self.wait_and_click(driver, By.CSS_SELECTOR, ".andes-pagination__button--next"):
                        wait_time = random.uniform(3, 6)
                        logger.info(f"⏳ Aguardando {wait_time:.1f}s antes de coletar página {page}...")
                        time.sleep(wait_time)
                        
                        page_products = self._scrape_page(driver)
                        products.extend(page_products)
                        logger.info(f"📦 Página {page}: {len(page_products)} produtos coletados (Total: {len(products)})")
                    else:
                        logger.info(f"🚫 Botão 'próxima página' não encontrado ou desabilitado. Parando coleta.")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao navegar para página {page} do {self.site_name}: {e}")
                    break
            
            logger.info(f"🎉 Coleta do {self.site_name} concluída! Total: {len(products)} produtos")
            
        except Exception as e:
            logger.error(f"❌ Erro no {self.site_name}: {e}")
        finally:
            logger.info(f"🔒 Fechando driver do {self.site_name}...")
            self.close_driver()
        
        return products
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            logger.info(f"🔍 Procurando por itens na página...")
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, ".ui-search-item")
            logger.info(f"📋 Encontrados {len(items)} itens na página")
            
            for i, item in enumerate(items, 1):
                try:
                    logger.debug(f"📝 Processando item {i}/{len(items)}...")
                    product = PS5Product()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do anúncio
                    title_elem = item.find_element(By.CSS_SELECTOR, ".ui-search-item__title")
                    product.nome_anuncio = title_elem.text.strip()
                    logger.debug(f"📄 Nome: {product.nome_anuncio[:50]}...")
                    
                    # Link
                    link_elem = item.find_element(By.CSS_SELECTOR, ".ui-search-link")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço à vista
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction")
                        product.preco_vista = self.clean_price(price_elem.text)
                        logger.debug(f"💰 Preço: R$ {product.preco_vista}")
                    except NoSuchElementException:
                        logger.debug(f"💰 Preço não encontrado")
                        pass
                    
                    # Preço parcelado
                    try:
                        installments_elem = item.find_element(By.CSS_SELECTOR, ".ui-search-price__second-line")
                        product.preco_parcelado = self.clean_price(installments_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
                    product.cor = self.extract_color(title_text)
                    product.com_leitor_disco = self.extract_disk_reader(title_text)
                    product.espaco_armazenamento = self.extract_storage(title_text)
                    product.jogos_incluidos = self.extract_games(title_text)
                    product.inclui_controles = self.extract_controllers(title_text)
                    
                    products.append(product)
                    logger.debug(f"✅ Item {i} processado com sucesso")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao processar item {i} do {self.site_name}: {e}")
                    continue
            
            logger.info(f"✅ Página processada: {len(products)} produtos coletados")
        
        except Exception as e:
            logger.error(f"❌ Erro ao scrapar página do {self.site_name}: {e}")
        
        return products


class KabumScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Kabum"""
    
    def __init__(self):
        super().__init__("Kabum")
        self.base_url = "https://www.kabum.com.br/gamer/playstation/consoles-playstation/playstation-5"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping da Kabum"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            time.sleep(3)
            
            # Aguarda carregar a página
            if not self.safe_find_element(driver, By.CSS_SELECTOR, ".productCard"):
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            for page in range(2, 8):
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, ".productCard")
            
            for item in items:
                try:
                    product = PS5Product()
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
    
    def __init__(self):
        super().__init__("Magazine Luiza")
        self.base_url = "https://www.magazineluiza.com.br/busca/ps5/"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping do Magazine Luiza"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            time.sleep(3)
            
            # Aguarda carregar a página
            if not self.safe_find_element(driver, By.CSS_SELECTOR, "[data-testid='product-card']"):
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            for page in range(2, 8):
                try:
                    if self.wait_and_click(driver, By.CSS_SELECTOR, "[data-testid='pagination-next']"):
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, "[data-testid='product-card']")
            
            for item in items:
                try:
                    product = PS5Product()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do produto
                    title_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='product-title']")
                    product.nome_anuncio = title_elem.text.strip()
                    
                    # Link
                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, "[data-testid='price-current']")
                        product.preco_vista = self.clean_price(price_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
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


class AmazonScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Amazon"""
    
    def __init__(self):
        super().__init__("Amazon")
        self.base_url = "https://www.amazon.com.br/s?k=ps5"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping da Amazon"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            time.sleep(3)
            
            # Aguarda carregar a página
            if not self.safe_find_element(driver, By.CSS_SELECTOR, "[data-component-type='s-search-result']"):
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            for page in range(2, 8):
                try:
                    if self.wait_and_click(driver, By.CSS_SELECTOR, ".s-pagination-next"):
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            
            for item in items:
                try:
                    product = PS5Product()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do produto
                    title_elem = item.find_element(By.CSS_SELECTOR, "h2 a span")
                    product.nome_anuncio = title_elem.text.strip()
                    
                    # Link
                    link_elem = item.find_element(By.CSS_SELECTOR, "h2 a")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, ".a-price-whole")
                        product.preco_vista = self.clean_price(price_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
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


class CasasBahiaScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Casas Bahia"""
    
    def __init__(self):
        super().__init__("Casas Bahia")
        self.base_url = "https://www.casasbahia.com.br/ps5/b"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping das Casas Bahia"""
        products = []
        
        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name}")
            
            driver.get(self.base_url)
            time.sleep(3)
            
            # Aguarda carregar a página
            if not self.safe_find_element(driver, By.CSS_SELECTOR, ".product-item"):
                logger.warning(f"Não foi possível carregar resultados do {self.site_name}")
                return products
            
            # Coleta produtos da primeira página
            products.extend(self._scrape_page(driver))
            
            # Tenta navegar para próximas páginas
            for page in range(2, 8):
                try:
                    if self.wait_and_click(driver, By.CSS_SELECTOR, ".pagination-next"):
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica"""
        products = []
        
        try:
            items = self.safe_find_elements(driver, By.CSS_SELECTOR, ".product-item")
            
            for item in items:
                try:
                    product = PS5Product()
                    product.site_origem = self.site_name
                    product.data_coleta = datetime.now().isoformat()
                    
                    # Nome do produto
                    title_elem = item.find_element(By.CSS_SELECTOR, ".product-title")
                    product.nome_anuncio = title_elem.text.strip()
                    
                    # Link
                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    product.link_pagina = link_elem.get_attribute("href")
                    
                    # Preço
                    try:
                        price_elem = item.find_element(By.CSS_SELECTOR, ".price")
                        product.preco_vista = self.clean_price(price_elem.text)
                    except NoSuchElementException:
                        pass
                    
                    # Extrai informações do título
                    title_text = product.nome_anuncio.lower()
                    product.modelo = self.extract_model(title_text)
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


def generate_statistics(products: List[PS5Product]) -> Dict:
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


def save_to_excel(products: List[PS5Product], filename: str = "ps5_products.xlsx"):
    """Salva os produtos em arquivo Excel"""
    try:
        df = pd.DataFrame([asdict(product) for product in products])
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info(f"Dados salvos em {filename}")
    except Exception as e:
        logger.error(f"Erro ao salvar Excel: {e}")


def main():
    """Função principal que executa todos os scrapers"""
    logger.info("🎮 === INICIANDO COLETA DE DADOS DE PS5 ===")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Lista de scrapers
    scrapers = [
        ("MercadoLivre", MercadoLivreScraper()),
        ("Kabum", KabumScraper()),
        ("Magazine Luiza", MagazineLuizaScraper()),
        ("Amazon", AmazonScraper()),
        ("Casas Bahia", CasasBahiaScraper()),
    ]
    
    all_products = []
    total_sites = len(scrapers)
    
    logger.info(f"🌐 Total de sites para coletar: {total_sites}")
    logger.info(f"📋 Sites: {', '.join([name for name, _ in scrapers])}")
    
    for site_num, (name, scraper) in enumerate(scrapers, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"🌐 SITE {site_num}/{total_sites}: {name}")
        logger.info(f"{'='*60}")
        
        try:
            start_time = time.time()
            products = scraper.scrape()
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"✅ {name} concluído em {duration:.1f}s - {len(products)} produtos coletados")
            all_products.extend(products)
            
            # Pausa entre scrapers para evitar bloqueios
            if site_num < total_sites:  # Não pausa após o último site
                pause_time = random.uniform(5, 10)
                logger.info(f"⏳ Pausando {pause_time:.1f}s antes do próximo site...")
                time.sleep(pause_time)
            
        except Exception as e:
            logger.error(f"❌ Erro ao coletar dados do {name}: {e}")
            continue
    
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
    
    # Converte para dicionário para JSON
    products_dict = [asdict(product) for product in unique_products]
    
    # Salva em arquivo JSON
    output_file = "ps5_products.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 Dados salvos em {output_file}")
    
    # Salva em Excel também
    save_to_excel(unique_products)
    
    # Gera estatísticas
    stats = generate_statistics(unique_products)
    
    logger.info(f"\n{'='*50}")
    logger.info("ESTATÍSTICAS FINAIS")
    logger.info(f"{'='*50}")
    
    logger.info(f"📈 Total de produtos: {stats['total_produtos']}")
    logger.info(f"💰 Produtos com preço: {stats['com_preco']}")
    logger.info(f"💿 Com leitor de disco: {stats['com_leitor_disco']}")
    logger.info(f"📱 Sem leitor de disco: {stats['sem_leitor_disco']}")
    logger.info(f"🎮 Com controles: {stats['com_controles']}")
    logger.info(f"🎯 Com jogos: {stats['com_jogos']}")
    
    logger.info(f"\n📊 Distribuição por site:")
    for site, count in stats['por_site'].items():
        logger.info(f"  {site}: {count}")
    
    logger.info(f"\n🎮 Distribuição por modelo:")
    for model, count in stats['por_modelo'].items():
        logger.info(f"  {model}: {count}")
    
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
    logger.info(f"  - {output_file}")
    logger.info(f"  - ps5_products.xlsx")
    logger.info(f"  - scraper.log")


if __name__ == "__main__":
    main()
