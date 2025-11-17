import json
import hashlib
import time
import re
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class BuscadorImovelInternet:
    """Busca REAL de imóveis na internet usando Selenium"""
    
    def __init__(self):
        self.driver = None
        self.imoveis = []
    
    def iniciar_driver(self):
        """Inicia o navegador Chrome com opções anti-bloqueio"""
        try:
            # Usar undetected-chromedriver para contornar Cloudflare
            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            self.driver = uc.Chrome(options=options, version_main=None)
            print("✓ Chrome (Undetected) inicializado com sucesso")
            return True
        except Exception as e:
            print(f"✗ Erro com undetected-chromedriver: {e}")
            try:
                # Fallback para Chrome normal
                options = Options()
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                self.driver = webdriver.Chrome(options=options)
                print("✓ Chrome (Normal) inicializado como fallback")
                return True
            except Exception as e2:
                print(f"✗ Erro ao iniciar Chrome: {e2}")
                return False
    
    def buscar_imovelweb(self, cidade="curitiba", paginas=2):
        """Busca real na ImóvelWeb"""
        print(f"\n🏠 Buscando em ImóvelWeb: {cidade.upper()}")
        print("  Aguarde, podem ser necessários 25-35 segundos...\n")
        
        try:
            # URL da ImóvelWeb - acessando a busca diretamente
            url = f"https://www.imovelweb.com.br/venda/apartamentos/{cidade}-pr"
            
            print(f"  Acessando: {url}")
            self.driver.get(url)
            
            # Esperar mais tempo para carregar completamente
            print("  ⏳ Carregando página...")
            time.sleep(5)
            
            # Scroll para carregar mais elementos
            for i in range(3):
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(2)
            
            # Extrair imóveis
            imoveis_encontrados = self._extrair_imoveis_imovelweb()
            self.imoveis.extend(imoveis_encontrados)
            
            print(f"  ✓ {len(imoveis_encontrados)} imóvel(is) encontrado(s)")
            return imoveis_encontrados
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:80]}")
            return []
    
    def _extrair_imoveis_imovelweb(self):
        """Extrai dados dos imóveis da página"""
        imoveis = []
        
        try:
            # Esperar mais tempo para carregar
            time.sleep(3)
            
            # Procurar por elementos de imóvel com múltiplos seletores
            listings = []
            
            # Tentar diferentes seletores usados em ImóvelWeb
            seletores = [
                "//div[contains(@class, 'listing')]",
                "//div[contains(@class, 'propiedad')]",
                "//div[@data-id]",
                "//article[contains(@class, 'item')]",
                "//li[contains(@class, 'resultsItem')]",
                "//div[contains(@id, 'listing-')]"
            ]
            
            for seletor in seletores:
                try:
                    listings = self.driver.find_elements(By.XPATH, seletor)
                    if listings and len(listings) > 0:
                        print(f"  ✓ Seletor encontrado: {len(listings)} elemento(s)")
                        break
                except:
                    continue
            
            print(f"  Processando {len(listings)} elemento(s)...")
            
            for listing in listings[:20]:
                try:
                    texto_completo = listing.text
                    
                    if not texto_completo or len(texto_completo) < 10:
                        continue
                    
                    # Procurar por link dentro do listing
                    link_elem = None
                    try:
                        link_elem = listing.find_element(By.TAG_NAME, "a")
                    except:
                        pass
                    
                    link = link_elem.get_attribute("href") if link_elem else None
                    
                    # Extrair informações com regex
                    linhas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
                    
                    # Título geralmente é a primeira linha significativa
                    titulo = linhas[0] if linhas else None
                    
                    if not titulo or len(titulo) < 5:
                        continue
                    
                    # Extrair preço
                    preco = None
                    preco_match = re.search(r"R\$\s*([\d.,]+)", texto_completo)
                    if preco_match:
                        preco = f"R$ {preco_match.group(1)}"
                    else:
                        preco = "Sob consulta"
                    
                    # Extrair metragem (m² ou m2)
                    metragem = None
                    area_match = re.search(r"(\d+)\s*m[²2]", texto_completo, re.IGNORECASE)
                    if area_match:
                        metragem = f"{area_match.group(1)} m²"
                    
                    # Extrair quartos
                    quartos = None
                    quartos_match = re.search(r"(\d+)\s*(?:quarto|q|q\.)", texto_completo.lower())
                    if quartos_match:
                        quartos = f"{quartos_match.group(1)} Q"
                    
                    # Extrair banheiros
                    banheiros = None
                    banheiros_match = re.search(r"(\d+)\s*(?:banheiro|b\.)", texto_completo.lower())
                    if banheiros_match:
                        banheiros = f"{banheiros_match.group(1)} B"
                    
                    # Criar ID único
                    uid = hashlib.md5(f"{titulo}{preco}".encode()).hexdigest()
                    
                    imovel = {
                        "id": uid,
                        "titulo": titulo[:100],
                        "preco": preco,
                        "metragem": metragem,
                        "quartos": quartos,
                        "banheiros": banheiros,
                        "link": link,
                        "fonte": "ImóvelWeb",
                        "data_coleta": datetime.now().isoformat()
                    }
                    imoveis.append(imovel)
                except Exception as e:
                    continue
            
            return imoveis
        
        except Exception as e:
            print(f"    Erro ao extrair: {str(e)[:50]}")
            return []
    
    def buscar_vivareal(self, cidade="curitiba"):
        """Busca real na VivaReal"""
        print(f"\n🏘️ Buscando em VivaReal: {cidade.upper()}")
        print("  Aguarde, podem ser necessários 20-25 segundos...\n")
        
        try:
            url = f"https://www.vivareal.com.br/venda/apartamentos/{cidade}-pr/"
            
            print(f"  Acessando: {url}")
            self.driver.get(url)
            
            # Aguardar carregamento
            print("  ⏳ Carregando página...")
            time.sleep(5)
            
            # Scroll para carregar mais
            for i in range(2):
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(2)
            
            # Extrair imóveis
            imoveis_encontrados = self._extrair_imoveis_vivareal()
            self.imoveis.extend(imoveis_encontrados)
            
            print(f"  ✓ {len(imoveis_encontrados)} imóvel(is) encontrado(s)")
            return imoveis_encontrados
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:80]}")
            return []
    
    def _extrair_imoveis_vivareal(self):
        """Extrai dados dos imóveis da VivaReal"""
        imoveis = []
        
        try:
            # Procurar por cards - VivaReal usa diferentes seletores
            cards = []
            
            seletores = [
                "//a[@data-testid='card-property']",
                "//div[contains(@class, 'card')]",
                "//div[contains(@class, 'Card_')]",
                "//article[contains(@class, 'Property')]",
                "//div[@data-component-name='Card']"
            ]
            
            for seletor in seletores:
                try:
                    cards = self.driver.find_elements(By.XPATH, seletor)
                    if cards and len(cards) > 0:
                        print(f"  ✓ Seletor encontrado: {len(cards)} elemento(s)")
                        break
                except:
                    continue
            
            print(f"  Processando {len(cards)} elemento(s)...")
            
            for card in cards[:20]:
                try:
                    texto = card.text
                    
                    if not texto or len(texto) < 5:
                        continue
                    
                    # Extrair preço
                    preco = None
                    preco_match = re.search(r"R\$\s*([\d.,]+)", texto)
                    if preco_match:
                        preco = f"R$ {preco_match.group(1)}"
                    else:
                        preco = "Sob consulta"
                    
                    # Extrair metragem
                    metragem = None
                    area_match = re.search(r"(\d+)\s*m[²2]", texto, re.IGNORECASE)
                    if area_match:
                        metragem = f"{area_match.group(1)} m²"
                    
                    # Extrair quartos
                    quartos = None
                    quartos_match = re.search(r"(\d+)\s*(?:quarto|q\.?)", texto.lower())
                    if quartos_match:
                        quartos = f"{quartos_match.group(1)} Q"
                    
                    # Título (geralmente primeira linha)
                    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
                    titulo = linhas[0] if linhas else "Imóvel"
                    
                    if len(titulo) < 5:
                        titulo = linhas[1] if len(linhas) > 1 else "Imóvel em VivaReal"
                    
                    # Link
                    link = None
                    try:
                        link_elem = card.find_element(By.TAG_NAME, "a")
                        link = link_elem.get_attribute("href")
                    except:
                        pass
                    
                    if len(titulo) > 3:
                        uid = hashlib.md5(f"{titulo}{preco}".encode()).hexdigest()
                        imovel = {
                            "id": uid,
                            "titulo": titulo[:100],
                            "preco": preco,
                            "metragem": metragem,
                            "quartos": quartos,
                            "link": link,
                            "fonte": "VivaReal",
                            "data_coleta": datetime.now().isoformat()
                        }
                        imoveis.append(imovel)
                except:
                    continue
            
            return imoveis
        
        except Exception as e:
            print(f"    Erro ao extrair: {str(e)[:50]}")
            return []
    
    def salvar(self, nome_arquivo=""):
        """Salva resultados em JSON"""
        if not self.imoveis:
            print("\n❌ Nenhum imóvel para salvar")
            return None
        
        # Remover duplicatas
        vistos = set()
        imoveis_unicos = []
        for im in self.imoveis:
            if im["id"] not in vistos:
                vistos.add(im["id"])
                imoveis_unicos.append(im)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not nome_arquivo:
            nome_arquivo = f"imoveis_internet_{timestamp}.json"
        
        caminho = OUTPUT_DIR / nome_arquivo
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(imoveis_unicos, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*70}")
        print(f"✅ {len(imoveis_unicos)} imóvel(is) encontrado(s) e salvo(s)")
        print(f"📁 Arquivo: {caminho.name}")
        print(f"{'='*70}\n")
        
        # Mostrar primeiros resultados
        print("📋 Primeiros resultados:\n")
        for i, im in enumerate(imoveis_unicos[:5], 1):
            print(f"{i}. {im['titulo']}")
            print(f"   💰 {im['preco']}")
            print(f"   📐 {im.get('metragem', 'N/A')}")
            print(f"   🌐 {im['fonte']}\n")
        
        if len(imoveis_unicos) > 5:
            print(f"   ... e {len(imoveis_unicos) - 5} mais")
        
        return str(caminho)
    
    def fechar(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()
            print("\n✓ Navegador fechado")


def main():
    import sys
    # Força UTF-8 no console Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("""
╔════════════════════════════════════════════════════════════════════╗
║      BUSCADOR DE IMÓVEIS NA INTERNET (BUSCA REAL COM SELENIUM)    ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    buscador = BuscadorImovelInternet()
    
    try:
        # Iniciar navegador
        if not buscador.iniciar_driver():
            print("❌ Não foi possível iniciar o navegador")
            return
        
        print("\n" + "="*70)
        print("Iniciando busca REAL na internet...")
        print("="*70)
        
        # Buscar em múltiplos sites
        buscador.buscar_imovelweb("sao-paulo")
        time.sleep(2)
        
        buscador.buscar_vivareal("sao-paulo")
        
        # Salvar resultados
        buscador.salvar()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Busca cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro geral: {type(e).__name__} - {str(e)[:100]}")
    finally:
        buscador.fechar()


if __name__ == "__main__":
    main()
