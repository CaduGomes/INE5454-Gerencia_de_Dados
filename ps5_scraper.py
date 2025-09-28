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
            # Usa o ChromeDriver com configurações simples
            self.driver = webdriver.Chrome(options=chrome_options)
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
    
    def extract_json_ld_products(self, driver) -> List[PS5Product]:
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
                            product = PS5Product()
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
    
    def scrape_product_page(self, driver, product_url: str) -> PS5Product:
        """Extrai dados de uma página individual de produto"""
        product = PS5Product()
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
        # URLs específicas para scraping
        self.target_urls = [
            "https://lista.mercadolivre.com.br/switch-2",
            "https://lista.mercadolivre.com.br/xbox-series-x", 
            "https://lista.mercadolivre.com.br/playstation-5",
            "https://lista.mercadolivre.com.br/xbox-series-s"
        ]
    
    def scrape(self) -> List[PS5Product]:
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
    
    def scrape_url_with_pagination(self, driver, base_url: str) -> List[PS5Product]:
        """Scrapa uma URL específica com paginação completa"""
        products = []
        current_page = 1
        max_pages = 50  # Limite de segurança para evitar loops infinitos
        
        try:
            logger.info(f"🌐 Navegando para: {base_url}")
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
            
            # Seletores para botão de próxima página - atualizados
            next_page_selectors = [
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
                    
                    # Verifica se o botão está habilitado e visível
                    if next_button.is_enabled() and next_button.is_displayed():
                        # Verifica se não está desabilitado
                        if "disabled" not in next_button.get_attribute("class").lower():
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
                        if "disabled" not in next_button.get_attribute("class").lower():
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
        """Scrapa uma página específica acessando cada produto individualmente"""
        products = []
        
        try:
            logger.info(f"🔍 Procurando por itens na página...")
            
            # Seletores atualizados para itens do Mercado Livre
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
            
            # Coleta URLs dos produtos primeiro
            product_urls = []
            for i, item in enumerate(items, 1):
                try:
                    # Busca por link do produto
                    link_selectors = [
                        ".ui-search-link",
                        ".ui-search-item__title a",
                        "a[data-testid='product-link']",
                        "a"
                    ]
                    
                    product_url = None
                    for link_selector in link_selectors:
                        try:
                            link_elem = item.find_element(By.CSS_SELECTOR, link_selector)
                            href = link_elem.get_attribute("href")
                            if href and "mercadolivre.com.br" in href and "/p/" in href:
                                product_url = href
                                break
                        except NoSuchElementException:
                            continue
                    
                    if product_url:
                        product_urls.append(product_url)
                        logger.debug(f"🔗 URL {i}: {product_url[:80]}...")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao extrair URL do item {i}: {e}")
                    continue
            
            logger.info(f"📦 Encontradas {len(product_urls)} URLs de produtos para processar")
            
            # Agora acessa cada página individual para coletar dados completos
            for i, product_url in enumerate(product_urls, 1):
                try:
                    logger.info(f"🔍 Processando produto {i}/{len(product_urls)}: {product_url[:80]}...")
                    
                    # Acessa a página do produto
                    product = self.scrape_product_page(driver, product_url)
                    
                    if product and product.nome_anuncio:
                        products.append(product)
                        logger.info(f"✅ Produto {i} coletado: {product.nome_anuncio[:50]}... - R$ {product.preco_vista}")
                    else:
                        logger.warning(f"⚠️ Produto {i} não pôde ser coletado")
                    
                    # Volta para a página de listagem se não for o último produto
                    if i < len(product_urls):
                        logger.debug(f"🔄 Voltando para página de listagem...")
                        driver.back()
                        self.wait_for_page_load(driver)
                        time.sleep(2)
                        
                        # Pausa entre produtos para evitar bloqueios
                        pause_time = random.uniform(1, 3)
                        logger.debug(f"⏳ Pausando {pause_time:.1f}s antes do próximo produto...")
                        time.sleep(pause_time)
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar produto {i}: {e}")
                    # Tenta voltar para a listagem em caso de erro
                    try:
                        driver.back()
                        self.wait_for_page_load(driver)
                        time.sleep(2)
                    except:
                        pass
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
    
    def scrape(self) -> List[PS5Product]:
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
    
    def __init__(self, debug_mode=False):
        super().__init__("Magazine Luiza", debug_mode)
        self.base_url = "https://www.magazineluiza.com.br/busca/ps5/"
    
    def scrape(self) -> List[PS5Product]:
        """Executa o scraping do Magazine Luiza"""
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
                "Cards de produtos": "[data-testid='product-card']",
                "Lista de produtos": ".product-list",
                "Grid de produtos": ".product-grid",
                "Container de produtos": ".product-container",
                "Itens de busca": ".search-item"
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


class CasasBahiaScraper(EnhancedBaseScraper):
    """Scraper aprimorado para Casas Bahia"""
    
    def __init__(self, debug_mode=False):
        super().__init__("Casas Bahia", debug_mode)
        self.base_url = "https://www.casasbahia.com.br/ps5/b"
    
    def scrape(self) -> List[PS5Product]:
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
            for page in range(2, 8):
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
    
    def _scrape_page(self, driver) -> List[PS5Product]:
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
                        
                    product = PS5Product()
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


def main(debug_mode=False):
    """Função principal que executa o scraper do Mercado Livre"""
    logger.info("🎮 === INICIANDO COLETA DE DADOS DO MERCADO LIVRE ===")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if debug_mode:
        logger.info("🐛 MODO DEBUG ATIVADO - Screenshots e HTML serão salvos")
    
    # Apenas o scraper do Mercado Livre
    scraper = MercadoLivreScraper(debug_mode)
    
    logger.info(f"🌐 URLs para coletar: {len(scraper.target_urls)}")
    logger.info(f"📋 URLs:")
    for i, url in enumerate(scraper.target_urls, 1):
        logger.info(f"  {i}. {url}")
    
    try:
        start_time = time.time()
        all_products = scraper.scrape()
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"✅ Mercado Livre concluído em {duration:.1f}s - {len(all_products)} produtos coletados")
        
    except Exception as e:
        logger.error(f"❌ Erro ao coletar dados do Mercado Livre: {e}")
        all_products = []
    
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
    output_file = "mercado_livre_products.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 Dados salvos em {output_file}")
    
    # Salva em Excel também
    excel_file = "mercado_livre_products.xlsx"
    save_to_excel(unique_products, excel_file)
    
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
    
    logger.info(f"\n📊 Distribuição por tipo de console:")
    for tipo, count in stats['por_modelo'].items():
        logger.info(f"  {tipo}: {count}")
    
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
    
    logger.info(f"\n✅ COLETA DO MERCADO LIVRE CONCLUÍDA COM SUCESSO!")
    logger.info(f"📁 Arquivos gerados:")
    logger.info(f"  - {output_file}")
    logger.info(f"  - {excel_file}")
    logger.info(f"  - scraper.log")


if __name__ == "__main__":
    import sys
    debug_mode = "--debug" in sys.argv
    main(debug_mode)
