#!/usr/bin/env python3
"""
Teste do ambiente para o scraper PS5
Verifica se todas as dependências estão funcionando
"""

import sys
import subprocess
import os
from datetime import datetime

def test_python_version():
    """Testa se a versão do Python é compatível"""
    print("🐍 Testando versão do Python...")
    if sys.version_info < (3, 7):
        print(f"❌ Python 3.7+ é necessário. Versão atual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def test_imports():
    """Testa se todas as dependências podem ser importadas"""
    print("\n📦 Testando importações...")
    
    dependencies = [
        ('requests', 'requests'),
        ('beautifulsoup4', 'bs4'),
        ('selenium', 'selenium'),
        ('pandas', 'pandas'),
        ('fake-useragent', 'fake_useragent'),
        ('openpyxl', 'openpyxl')
    ]
    
    all_ok = True
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError as e:
            print(f"❌ {package_name}: {e}")
            all_ok = False
    
    return all_ok

def test_chrome():
    """Testa se o Chrome está disponível"""
    print("\n🌐 Testando Chrome...")
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Chrome encontrado: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("❌ Chrome não encontrado")
    return False

def test_chromedriver():
    """Testa se o ChromeDriver está disponível"""
    print("\n🚗 Testando ChromeDriver...")
    try:
        result = subprocess.run(['chromedriver', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ ChromeDriver encontrado: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("❌ ChromeDriver não encontrado")
    return False

def test_scraper_import():
    """Testa se o scraper pode ser importado"""
    print("\n🔧 Testando importação do scraper...")
    try:
        from ps5_scraper import MercadoLivreScraper
        print("✅ Scraper importado com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar scraper: {e}")
        return False

def test_simple_scrape():
    """Testa um scraping simples"""
    print("\n🎮 Testando scraping simples...")
    try:
        from ps5_scraper import MercadoLivreScraper
        
        scraper = MercadoLivreScraper()
        print("✅ Scraper criado com sucesso")
        
        # Testa apenas a criação do driver (sem executar)
        driver = scraper.get_driver()
        if driver:
            print("✅ Driver do Chrome criado com sucesso")
            scraper.close_driver()
            return True
        else:
            print("❌ Falha ao criar driver")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de scraping: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🎮 === TESTE DO AMBIENTE PS5 SCRAPER ===")
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    
    tests = [
        ("Versão do Python", test_python_version),
        ("Dependências Python", test_imports),
        ("Google Chrome", test_chrome),
        ("ChromeDriver", test_chromedriver),
        ("Importação do Scraper", test_scraper_import),
        ("Teste Simples", test_simple_scrape),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Teste: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            results.append((test_name, False))
    
    # Resumo dos testes
    print(f"\n{'='*50}")
    print("📊 RESUMO DOS TESTES")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram! O ambiente está pronto.")
        print("\nPara executar o scraper completo, use:")
        print("python3 ps5_scraper.py")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique as dependências.")
        print("\nPara instalar dependências, use:")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    main()

