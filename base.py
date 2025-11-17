import time
import hashlib
from playwright.sync_api import sync_playwright

class ImoveisScraper:
    def __init__(self):
        self.play = sync_playwright().start()
        self.browser = self.play.chromium.launch(headless=False)  # manter visível melhora a liberação do Cloudflare
        self.page = self.browser.new_page()
        self.resultados = []

    def normalize(self, item, estado):
        clean_id = hashlib.md5(str(item.get("id")).encode()).hexdigest()
        return {
            "id": clean_id,
            "titulo": item.get("title"),
            "preco": item.get("price"),
            "metragem": item.get("size"),
            "bairro": item.get("location", {}).get("neighborhood"),
            "cidade": item.get("location", {}).get("municipality"),
            "estado": estado.upper(),
            "cep": item.get("zip"),
            "link": item.get("url"),
            "timestamp": time.time()
        }

    def coletar_olx(self, estado="pr", pages=1):

        # intercepta as APIs internas
        def intercept(route, request):
            if "items?" in request.url:
                try:
                    response = self.page.request.fetch(request)
                    data = response.json().get("data", [])
                    for item in data:
                        self.resultados.append(self.normalize(item, estado))
                except:
                    pass
            route.continue_()

        self.page.route("**/*", intercept)

        for p in range(1, pages + 1):
            url = f"https://www.olx.com.br/imoveis/{estado}?o={p}"
            self.page.goto(url, timeout=60000)
            self.page.wait_for_timeout(3000)

            print(f"{estado} página {p} carregada.")

        return self.resultados

    def close(self):
        self.browser.close()
        self.play.stop()


scraper = ImoveisScraper()
dados = scraper.coletar_olx("sp", pages=3)
scraper.close()

print("Total coletado:", len(dados))
