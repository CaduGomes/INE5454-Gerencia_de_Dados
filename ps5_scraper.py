#!/usr/bin/env python3
"""
Web Scraper Avançado para Magazine Luiza (PS5 / Consoles)
Disciplina: INE5454 - Gerência de Dados
Versão: 3.0 - Magazine Luiza hardened (gestão de consentimento, lazy-load, paginação, snapshots)

Execução:
    python magalu_scraper.py
    python magalu_scraper.py --debug     # salva snapshots (PNG/HTML) em ./snapshots
"""

import json
import time
import random
import re
import logging
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# Selenium + WebDriver Manager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent


# --------------------------- LOGGING ---------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


# --------------------------- MODELOS ---------------------------


@dataclass
class PS5Product:
    """Modelo de produto genérico (usado também para outros consoles)."""

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
    marca: str = ""
    site_origem: str = ""
    data_coleta: str = ""
    disponibilidade: str = ""


# --------------------- BASE SCRAPER APRIMORADA ---------------------


class EnhancedBaseScraper:
    """Classe base com utilitários robustos para scrapers com Selenium."""

    def __init__(self, site_name: str, debug_mode: bool = False):
        self.site_name = site_name
        self.debug_mode = debug_mode
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update(
            {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.driver: Optional[webdriver.Chrome] = None

    def get_with_timeout(self, driver, url: str, timeout: int = 20) -> bool:
        """
        Navigate with a hard timeout. If it times out, abort remaining loads via window.stop()
        so the script can proceed with explicit waits. Returns True if no timeout, False otherwise.
        """
        try:
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            return True
        except TimeoutException:
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
            return False

    def get_driver(self) -> webdriver.Chrome:
        """Cria (ou reutiliza) um driver Chrome com opções endurecidas."""
        if self.driver:
            return self.driver

        opts = Options()
        # Visível por padrão (mais confiável). Mude para headless se quiser.
        # opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1366,960")

        # Reduz fingerprint de automação
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        # Preferências de idioma
        opts.add_argument("--lang=pt-BR")
        opts.add_experimental_option(
            "prefs",
            {"intl.accept_languages": "pt-BR,pt;q=0.9,en;q=0.8"},
        )

        # User-Agent "comum"
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            # Esconde navigator.webdriver
            try:
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                    },
                )
            except Exception:
                pass

            return self.driver
        except Exception as e:
            logger.error(f"Erro ao criar driver do Chrome: {e}")
            raise

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # ------------------- Utilitários de texto -------------------

    def clean_price(self, price_text: str) -> str:
        """Normaliza preço: mantém dígitos e vírgula/ponto; força decimal único."""
        if not price_text:
            return ""
        price = re.sub(r"[^\d,.]", "", price_text).replace(",", ".")
        if "." in price:
            parts = price.split(".")
            if len(parts) > 2:
                price = "".join(parts[:-1]) + "." + parts[-1]
        return price

    def extract_storage(self, text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        for pat, repl in [
            (r"(\d+)\s*gb", r"\1 GB"),
            (r"(\d+)\s*tb", r"\1 TB"),
            (r"(\d+)\s*terabyte", r"\1 TB"),
            (r"(\d+)\s*gigabyte", r"\1 GB"),
        ]:
            m = re.search(pat, t)
            if m:
                return re.sub(pat, repl, t)
        return ""

    def extract_disk_reader(self, text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        if any(
            x in t
            for x in [
                "com leitor",
                "leitor de disco",
                "disc version",
                "versão com leitor",
                "com disco",
            ]
        ):
            return "Sim"
        if any(
            x in t
            for x in [
                "sem leitor",
                "digital",
                "digital edition",
                "slim",
                "edição digital",
            ]
        ):
            return "Não"
        return ""

    def extract_color(self, text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        colors = [
            "branco",
            "preto",
            "azul",
            "vermelho",
            "dourado",
            "prata",
            "cinza",
            "white",
            "black",
            "blue",
            "red",
        ]
        for c in colors:
            if c in t:
                return c.capitalize()
        return ""

    def extract_controllers(self, text: str) -> str:
        if not text:
            return "Não"
        t = text.lower()
        return (
            "Sim"
            if any(
                x in t
                for x in ["controle", "dualsense", "joystick", "gamepad", "controller"]
            )
            else "Não"
        )

    def extract_games(self, text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        hits = []
        common = [
            "spider-man",
            "ratchet",
            "clank",
            "horizon",
            "forbidden west",
            "demon's souls",
            "returnal",
            "sackboy",
            "astros playroom",
            "god of war",
            "the last of us",
            "uncharted",
        ]
        for g in common:
            if g in t:
                hits.append(g.replace("'", "").title())
        return ", ".join(hits) if hits else ""

    def extract_model(self, text: str) -> str:
        if not text:
            return ""
        t = text.lower()
        if "slim" in t:
            return "PS5 Slim"
        if "digital" in t or "edição digital" in t:
            return "PS5 Digital Edition"
        if "ps5" in t or "playstation 5" in t:
            return "PS5 Standard"
        if "xbox" in t:
            return "Xbox"
        if "switch" in t or "nintendo" in t:
            return "Nintendo Switch"
        return ""

    # ------------------- Selenium helpers -------------------

    def wait_and_click(self, driver, by, value, timeout=10) -> bool:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            driver.execute_script("arguments[0].click();", el)
            return True
        except TimeoutException:
            return False

    def safe_find_element(self, driver, by, value, timeout=5):
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def safe_find_elements(self, driver, by, value, timeout=5):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return driver.find_elements(by, value)
        except TimeoutException:
            return []

    def wait_for_page_load(self, driver, timeout=15) -> bool:
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False

    # ------------------- Snapshots (PNG + HTML) -------------------

    def _safe_filename(self, s: str) -> str:
        s = re.sub(r"[^\w.-]+", "_", s)
        return s[:160]

    def save_snapshot(
        self, driver, label: str, out_dir: str = "snapshots"
    ) -> Tuple[str, str]:
        """Salva screenshot e HTML do que o Selenium está vendo (sem exceção)."""
        if not self.debug_mode:
            return "", ""
        try:
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            base = f"{ts}_{self._safe_filename(label)}"
            png_path = os.path.join(out_dir, base + ".png")
            html_path = os.path.join(out_dir, base + ".html")
            driver.save_screenshot(png_path)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source or "")
            logger.info(f"📸 Snapshot salvo: {png_path}")
            logger.info(f"📄 HTML salvo: {html_path}")
            return png_path, html_path
        except Exception as e:
            logger.warning(f"Falha ao salvar snapshot ({label}): {e}")
            return "", ""


# --------------------- MAGAZINE LUIZA SCRAPER ---------------------


class MagazineLuizaScraper(EnhancedBaseScraper):
    """Scraper robusto para Magazine Luiza (lista + produtos + paginação)."""

    def __init__(self, debug_mode=False):
        super().__init__("Magazine Luiza", debug_mode)
        self.base_url = "https://www.magazineluiza.com.br/busca/ps5/"

    # ---- Consent + list waits ----

    def wait_for_product_list_interactable(self, driver, timeout: int = 20) -> None:
        """
        Wait until the product list UL is visible and interactable-ish.
        - Prefers ul[data-testid='list']; falls back to [data-testid='product-list'].
        - Ensures element is displayed, within viewport, and not covered by an overlay.
        Raises TimeoutException on failure.
        """
        selectors = [
            "ul[data-testid='list']",
            "[data-testid='product-list']",
        ]

        def _visible_and_unblocked(d):
            el = None
            for sel in selectors:
                els = d.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    el = els[0]
                    break
            if not el:
                return False
            if not el.is_displayed():
                return False

            # In viewport?
            try:
                d.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            except Exception:
                pass

            # Check if an overlay blocks clicks: elementFromPoint at the center should be inside 'el'
            try:
                box = d.execute_script(
                    """
                    const r = arguments[0].getBoundingClientRect();
                    return {x: (r.left + r.right)/2, y: (r.top + r.bottom)/2};
                """,
                    el,
                )
                topEl = d.execute_script(
                    "return document.elementFromPoint(arguments[0], arguments[1]);",
                    box["x"],
                    box["y"],
                )
                # Walk up the DOM to see if the hit element belongs to the list
                same_or_child = d.execute_script(
                    """
                    const target = arguments[0], root = arguments[1];
                    let n = target;
                    while (n) {
                        if (n === root) return true;
                        n = n.parentElement;
                    }
                    return false;
                """,
                    topEl,
                    el,
                )
                if not same_or_child:
                    return False
            except Exception:
                # If JS fails, fall back to simple visibility
                return el.is_displayed()

            return True

        WebDriverWait(driver, timeout).until(_visible_and_unblocked)

    def _handle_magalu_consent(self, driver):
        """Fecha banners de consentimento (best-effort)."""
        selectors = [
            "[data-testid='lgpd-accept-button']",
            "button[id*='lgpd'][id*='accept']",
            "button[aria-label*='aceitar' i]",
            "button[aria-label*='concordo' i]",
        ]
        for sel in selectors:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(0.2)
                        return
            except Exception:
                pass

    def _wait_results_and_scroll(self, driver, min_cards=10, max_scrolls=8):
        """Aguarda containers plausíveis e realiza scroll incremental p/ lazy-load."""
        containers = [
            "[data-testid='product-list']",
            "section[data-testid='search-results']",
            "main",
        ]
        for sel in containers:
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                break
            except TimeoutException:
                continue

        last_h = 0
        for i in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8 + 0.2 * i)
            new_h = driver.execute_script("return document.body.scrollHeight;")
            if new_h == last_h:
                break
            last_h = new_h
            if (
                len(
                    driver.find_elements(
                        By.CSS_SELECTOR, "[data-testid='product-card']"
                    )
                )
                >= min_cards
            ):
                break

    # ---- Product page ----

    def _scrape_product_page(self, driver, product_url: str) -> PS5Product:
        p = PS5Product()
        p.site_origem = self.site_name
        p.data_coleta = datetime.now().isoformat()
        p.link_pagina = product_url

        try:
            driver.get(product_url)
            self.wait_for_page_load(driver)
            self._handle_magalu_consent(driver)
            time.sleep(1.0)

            self.save_snapshot(driver, f"product_enter_{product_url}")

            # Título
            title = ""
            for sel in [
                "[data-testid='product-title']",
                "h1",
                "[data-testid='Heading'] h1",
            ]:
                try:
                    el = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    t = el.text.strip()
                    if t:
                        title = t
                        break
                except TimeoutException:
                    continue
            p.nome_anuncio = title

            # Preço
            price_text = ""
            price_sels = [
                "[data-testid='price-current']",
                "[data-testid='price-value']",
                "[class*='price'] [data-testid*='price']",
                "[class*='price']",
            ]
            for sel in price_sels:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for e in els:
                    txt = e.text.strip()
                    if txt and "R$" in txt:
                        price_text = txt
                        break
                if price_text:
                    break
            if not price_text:
                # Fallback: JSON-LD (Product.offers.price)
                try:
                    for sc in driver.find_elements(
                        By.CSS_SELECTOR, 'script[type="application/ld+json"]'
                    ):
                        try:
                            data = json.loads(sc.get_attribute("innerHTML") or "{}")
                        except json.JSONDecodeError:
                            continue
                        if isinstance(data, dict) and data.get("@type") == "Product":
                            offers = data.get("offers") or {}
                            if isinstance(offers, dict) and offers.get("price"):
                                price_text = str(offers["price"])
                                break
                        if isinstance(data, list):
                            for item in data:
                                if (
                                    isinstance(item, dict)
                                    and item.get("@type") == "Product"
                                ):
                                    offers = item.get("offers") or {}
                                    if isinstance(offers, dict) and offers.get("price"):
                                        price_text = str(offers["price"])
                                        break
                            if price_text:
                                break
                except Exception:
                    pass
            p.preco_vista = self.clean_price(price_text)

            # Descrição (opcional, para enriquecer extrações)
            description_text = ""
            for sel in [
                "[data-testid='description']",
                "[class*='product-description']",
                "section[id*='descricao']",
            ]:
                try:
                    node = driver.find_element(By.CSS_SELECTOR, sel)
                    if node and node.text.strip():
                        description_text = node.text.strip()
                        break
                except NoSuchElementException:
                    continue

            combo = f"{p.nome_anuncio} {description_text}".lower()
            p.modelo = self.extract_model(combo)
            p.cor = self.extract_color(combo)
            p.com_leitor_disco = self.extract_disk_reader(combo)
            p.espaco_armazenamento = self.extract_storage(combo)
            p.jogos_incluidos = self.extract_games(combo)
            p.inclui_controles = self.extract_controllers(combo)

            # Tipo/marca heurístico
            if any(k in combo for k in ("nintendo", "switch")):
                p.tipo, p.marca = "Console Nintendo Switch", "Nintendo"
            elif any(k in combo for k in ("xbox",)):
                p.tipo, p.marca = "Console Xbox", "Microsoft"
            elif any(k in combo for k in ("playstation", "ps5", "ps 5", "ps-5")):
                p.tipo, p.marca = "Console PlayStation", "Sony"

            self.save_snapshot(driver, f"product_post_{product_url}")

        except Exception as e:
            logger.debug(f"Erro em produto {product_url}: {e}")

        return p

    # ---- List page + pagination ----

    def _collect_listing_cards(self, driver) -> List:
        return driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='product-card-container']"
        )

    def _collect_product_urls_from_cards(self, cards) -> List[str]:
        urls = []
        for c in cards:
            try:
                href = c.get_attribute("href")
                if href and href.startswith("http"):
                    urls.append(href)
            except Exception:
                continue
        return urls

    def _go_to_next_page(self, driver) -> bool:
        """Clica 'próxima página' e espera o DOM mudar (staleness)."""
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.7)
        except Exception:
            pass

        sentinel_cards = self._collect_listing_cards(driver)
        sentinel = sentinel_cards[0] if sentinel_cards else None

        for sel in [
            "[data-testid='pagination-item']",
            "a[aria-label='Próxima página']",
            "button[aria-label='Próxima página']",
            "a[rel='next']",
        ]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    break
            except Exception:
                continue
        else:
            logger.info("❌ Próxima página não encontrada")
            return False

        try:
            if sentinel:
                WebDriverWait(driver, 20).until(EC.staleness_of(sentinel))
            self.wait_for_page_load(driver)
            self._handle_magalu_consent(driver)
            self._wait_results_and_scroll(driver)
            self.save_snapshot(driver, f"listing_next_{int(time.time())}")
            return True
        except TimeoutException:
            return False

    def scrape(self) -> List[PS5Product]:
        """Executa o scraping da Magazine Luiza (listagem + produtos + paginação)."""
        products: List[PS5Product] = []

        try:
            driver = self.get_driver()
            logger.info(f"Iniciando coleta do {self.site_name} em {self.base_url}")

            self.get_with_timeout(
                driver, self.base_url, timeout=15
            )  # or your open_magalu_results()
            self._handle_magalu_consent(driver)
            self.wait_for_product_list_interactable(driver, timeout=25)
            self.save_snapshot(driver, "magalu_listing_enter")

            current_page = 1
            max_pages = 50

            while current_page <= max_pages:
                logger.info(f"📄 Processando página {current_page} (Magalu)…")

                cards = self._collect_listing_cards(driver)
                if not cards:
                    logger.warning("Nenhum card encontrado; tentando scrolar mais…")
                    self._wait_results_and_scroll(driver)
                    cards = self._collect_listing_cards(driver)

                urls = self._collect_product_urls_from_cards(cards)
                urls = urls[:5]
                logger.info(f"🔗 {len(urls)} URLs de produto encontradas nesta página.")

                for i, url in enumerate(urls, 1):
                    try:
                        logger.info(f"  → Produto {i}/{len(urls)}")
                        p = self._scrape_product_page(driver, url)
                        if p and p.nome_anuncio:
                            products.append(p)
                            logger.info(
                                f"    ✅ {p.nome_anuncio[:70]} - R$ {p.preco_vista}"
                            )
                        else:
                            logger.info("    ⚠️ Produto sem título; ignorado.")

                        if i < len(urls):
                            driver.back()
                            self.wait_for_page_load(driver)
                            time.sleep(random.uniform(0.8, 1.6))
                    except Exception as e:
                        logger.warning(f"    ⚠️ Erro no produto {i}: {e}")
                        try:
                            driver.back()
                            self.wait_for_page_load(driver)
                        except Exception:
                            pass
                        time.sleep(1.0)

                if not self._go_to_next_page(driver):
                    logger.info("✅ Última página alcançada (Magalu).")
                    break

                current_page += 1
                time.sleep(random.uniform(1.5, 3.0))

            logger.info(f"Coletados {len(products)} produtos do {self.site_name}")

        except Exception as e:
            logger.error(f"Erro no {self.site_name}: {e}")
        finally:
            self.close_driver()

        return products


# --------------------- PÓS-PROCESSAMENTO ---------------------


def generate_statistics(products: List[PS5Product]) -> Dict:
    stats = {
        "total_produtos": len(products),
        "por_site": {},
        "por_modelo": {},
        "com_preco": 0,
        "com_leitor_disco": 0,
        "sem_leitor_disco": 0,
        "com_controles": 0,
        "com_jogos": 0,
        "cores": {},
        "armazenamento": {},
    }
    for p in products:
        stats["por_site"][p.site_origem] = stats["por_site"].get(p.site_origem, 0) + 1
        modelo = p.modelo or "Não especificado"
        stats["por_modelo"][modelo] = stats["por_modelo"].get(modelo, 0) + 1
        if p.preco_vista:
            stats["com_preco"] += 1
        if p.com_leitor_disco == "Sim":
            stats["com_leitor_disco"] += 1
        elif p.com_leitor_disco == "Não":
            stats["sem_leitor_disco"] += 1
        if p.inclui_controles == "Sim":
            stats["com_controles"] += 1
        if p.jogos_incluidos:
            stats["com_jogos"] += 1
        if p.cor:
            stats["cores"][p.cor] = stats["cores"].get(p.cor, 0) + 1
        if p.espaco_armazenamento:
            stats["armazenamento"][p.espaco_armazenamento] = (
                stats["armazenamento"].get(p.espaco_armazenamento, 0) + 1
            )
    return stats


def save_to_excel(products: List[PS5Product], filename: str = "magalu_products.xlsx"):
    try:
        df = pd.DataFrame([asdict(p) for p in products])
        df.to_excel(filename, index=False, engine="openpyxl")
        logger.info(f"Dados salvos em {filename}")
    except Exception as e:
        logger.error(f"Erro ao salvar Excel: {e}")


# --------------------------- MAIN ---------------------------


def main(debug_mode=False):
    logger.info("🎮 === INICIANDO COLETA DE DADOS: MAGAZINE LUIZA ===")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    if debug_mode:
        logger.info("🐛 MODO DEBUG ATIVADO - Snapshots serão salvos em ./snapshots")

    scraper = MagazineLuizaScraper(debug_mode)
    try:
        start = time.time()
        products = scraper.scrape()
        dur = time.time() - start
        logger.info(
            f"✅ Magazine Luiza concluído em {dur:.1f}s - {len(products)} produtos coletados"
        )
    except Exception as e:
        logger.error(f"Erro na coleta: {e}")
        products = []

    # Dedup por link
    unique, seen = [], set()
    for p in products:
        if p.link_pagina and p.link_pagina not in seen:
            seen.add(p.link_pagina)
            unique.append(p)

    logger.info(f"📊 Total de produtos únicos: {len(unique)}")

    # Salva JSON + Excel
    json_path = "magalu_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in unique], f, ensure_ascii=False, indent=2)
    logger.info(f"💾 JSON salvo em {json_path}")

    save_to_excel(unique, "magalu_products.xlsx")

    # Estatísticas
    stats = generate_statistics(unique)
    logger.info("\n===== ESTATÍSTICAS FINAIS =====")
    logger.info(f"Total de produtos: {stats['total_produtos']}")
    logger.info(f"Com preço: {stats['com_preco']}")
    logger.info(f"Com leitor de disco: {stats['com_leitor_disco']}")
    logger.info(f"Sem leitor de disco: {stats['sem_leitor_disco']}")
    logger.info(f"Com controles: {stats['com_controles']}")
    logger.info(f"Com jogos: {stats['com_jogos']}")

    logger.info("\n📊 Por modelo:")
    for k, v in stats["por_modelo"].items():
        logger.info(f"  {k}: {v}")

    if stats["cores"]:
        logger.info("\n🎨 Cores:")
        for k, v in stats["cores"].items():
            logger.info(f"  {k}: {v}")

    if stats["armazenamento"]:
        logger.info("\n💾 Armazenamento:")
        for k, v in stats["armazenamento"].items():
            logger.info(f"  {k}: {v}")

    logger.info("\n✅ COLETA CONCLUÍDA! Arquivos gerados:")
    logger.info("  - magalu_products.json")
    logger.info("  - magalu_products.xlsx")
    logger.info("  - scraper.log")
    if debug_mode:
        logger.info("  - snapshots/*.png + *.html")


if __name__ == "__main__":
    import sys

    main(debug_mode="--debug" in sys.argv)
