import requests
import json
import os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "caixa")
os.makedirs(OUTPUT_DIR, exist_ok=True)

URL_API = "https://venda-imoveis.caixa.gov.br/sistema/PortalImoveisCaixa/Imovel/ConsultaImoveis"

def coletar_imoveis_por_estado(estado="PR"):
    print(f"Buscando imóveis (API Caixa corrigida) — Estado: {estado}")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://venda-imoveis.caixa.gov.br/sistema/PortalImoveisCaixa/Imovel/ConsultaIniciar",
        "Content-Type": "application/json"
    }

    payload = {
        "pagina": 1,
        "quantidade": 5000,
        "uf": estado,
        "cidade": "",
        "bairro": "",
        "tipopropriedade": "",
        "tipoimovel": "",
        "situacaoimovel": "",
        "codigopostal": ""
    }

    response = requests.post(URL_API, headers=headers, json=payload)

    # Se não vier JSON, mostrar erro bruto
    try:
        data = response.json()
    except Exception:
        print("\nResposta não é JSON. Conteúdo recebido:")
        print(response.text[:500])
        return

    registros = []

    for item in data.get("imoveis", []):
        registros.append({
            "cidade": item.get("cidade"),
            "uf": item.get("uf"),
            "bairro": item.get("bairro"),
            "endereco": item.get("endereco"),
            "valor_avaliacao": item.get("valoravaliacao"),
            "valor_minimo": item.get("valorminimo"),
            "area_total": item.get("areaprivativa"),
            "tipo_imovel": item.get("tipoimovel"),
            "modalidade_venda": item.get("modalidadevenda"),
            "link_edital": item.get("urldetalhes"),
            "fonte": "Caixa",
            "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    nome_json = f"caixa_api_{estado}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    caminho_json = os.path.join(OUTPUT_DIR, nome_json)

    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)

    print(f"Total coletado: {len(registros)}")
    print(f"Arquivo salvo: {caminho_json}")

    return caminho_json


if __name__ == "__main__":
    coletar_imoveis_por_estado("PR")
