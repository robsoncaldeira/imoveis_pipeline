#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIA PRÁTICO: Como usar o sistema passo-a-passo
Mostra os comandos exatos para coletar imóveis de múltiplas buscas
"""

def main():
    guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║  🏠 GUIA PRÁTICO: Como Coletar 50k+ Imóveis com Este Sistema              ║
╚════════════════════════════════════════════════════════════════════════════╝

PASSO 1: Coletar URLs (MANUAL COM CAPTCHA)
═════════════════════════════════════════════════════════════════════════════

Abra um terminal e execute para cada palavra-chave:

  $ python busca_ampla.py "apartamento são paulo"
  
  O que acontece:
  ├─ Navegador abre automaticamente
  ├─ Você vê as buscas sendo feitas no Bing
  ├─ Se aparecer CAPTCHA → Resolve manualmente
  ├─ Aperta Enter no terminal
  └─ JSON salvo com ~19 URLs

  Repita para múltiplas buscas:
  
  $ python busca_ampla.py "apartamento rio de janeiro"
  $ python busca_ampla.py "casa brasília"
  $ python busca_ampla.py "quarto curitiba"
  $ python busca_ampla.py "apartamento salvador"
  $ python busca_ampla.py "casa porto alegre"
  $ python busca_ampla.py "apartamento fortaleza"
  $ python busca_ampla.py "imóvel recife"
  $ python busca_ampla.py "apartamento manaus"
  $ python busca_ampla.py "casa goiânia"
  
  Resultado: 10 buscas × 19 URLs = ~190 URLs totais

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PASSO 2: Processar URLs → Dados → CSV (SEM INTERVENÇÃO)
═════════════════════════════════════════════════════════════════════════════

Depois de fazer todas as buscas, execute uma vez:

  $ python integrar.py -w 5 --headless
  
  O que acontece:
  ├─ Lê todos os JSONs de busca_ampla
  ├─ Insere ~190 URLs no banco SQLite
  ├─ Processa 5 URLs em paralelo (5 navegadores)
  ├─ Extrai: preço, endereço, CEP, telefone, etc
  ├─ Salva no SQLite (banco de dados)
  ├─ Exporta para CSV
  └─ Tempo: ~15-20 minutos para 190 URLs

  Resultado:
  ├─ Banco: imoveis.db (150+ imóveis)
  └─ CSV: output/imoveis_scraper_escalavel_TIMESTAMP.csv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PASSO 3: Consolidar em Um Único CSV (OPCIONAL)
═════════════════════════════════════════════════════════════════════════════

Se fizer múltiplas rodadas de integrar.py, consolide em um arquivo:

  $ python consolidar.py
  
  Resultado: output/imoveis_consolidado_TIMESTAMP.csv
  ├─ Remove duplicatas
  └─ Total de imóveis únicos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PASSO 4: Verificar Resultados
═════════════════════════════════════════════════════════════════════════════

Para ver estatísticas do banco:

  $ python stats.py
  
  Mostra:
  ├─ Total de imóveis coletados
  ├─ Por domínio
  ├─ Cobertura de dados (% com preço, endereço, CEP, etc)
  └─ Amostra

Para ver a arquitetura completa:

  $ python resumo.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXEMPLO: ESCALAR PARA 200+ IMÓVEIS EM 30 MINUTOS
═════════════════════════════════════════════════════════════════════════════

Terminal 1 (Manual - CAPTCHA):
──────────────────────────────
$ python busca_ampla.py "apartamento são paulo"      # 3 min
$ python busca_ampla.py "apartamento rio"            # 3 min
$ python busca_ampla.py "apartamento minas"          # 3 min
$ python busca_ampla.py "casa brasília"              # 3 min
$ python busca_ampla.py "quarto recife"              # 3 min
$ python busca_ampla.py "apartamento salvador"       # 3 min
$ python busca_ampla.py "casa porto alegre"          # 3 min
[Total: ~21 min, ~130 URLs coletadas]

Terminal 2 (Automático - SEM INTERVENÇÃO):
──────────────────────────────────────────
[Espera Terminal 1 terminar]
$ python integrar.py -w 5
[Total: ~15 min, 200+ imóveis processados, CSV exportado]

TEMPO TOTAL: ~36 minutos
RESULTADO: 200+ imóveis em CSV com: preço, endereço, CEP, contato

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DICAS IMPORTANTES
═════════════════════════════════════════════════════════════════════════════

1. CAPTCHA MUITO FREQUENTE?
   └─ Adicione delay entre buscas (sleep 10s)
   └─ Ou use proxy (futura feature)

2. MAIS WORKERS = MAIS RÁPIDO?
   └─ Sim, mas aumenta uso de RAM
   └─ Máx recomendado: 10 workers
   └─ Se travar, volte para 5

3. DADOS INCOMPLETOS (SEM ENDEREÇO)?
   └─ Normal em alguns domínios
   └─ Mercado Livre tem JSON-LD estruturado
   └─ OLX/VivaReal: melhores com regex

4. COMO ADICIONAR MAIS BUSCAS?
   └─ Repita "busca_ampla.py" com nova palavra-chave
   └─ Execute "integrar.py" depois
   └─ Não precisa fazer tudo de novo

5. PAROU NO MEIO DO PROCESSAMENTO?
   └─ Nenhum problema! Pode re-executar "integrar.py"
   └─ SQLite salva progresso (checkpoint)
   └─ Continua de onde parou

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TROUBLESHOOTING
═════════════════════════════════════════════════════════════════════════════

Erro: "Nenhum arquivo JSON encontrado"
├─ Solução: Você rodou "busca_ampla.py" antes?
└─ Execute: python busca_ampla.py "sua busca"

Erro: "Bing is presenting a challenge"
├─ Solução: Browser está aberto? Resolve CAPTCHA manualmente
└─ Aperta Enter depois

Erro: "Gateway timeout" (OLX/Mercado Livre)
├─ Solução: Site está sobrecarregado
└─ Tenta novamente depois

CSV vazio ou com 0 imóveis
├─ Solução: JSON não foi lido corretamente
└─ Execute: python stats.py (para verificar banco)

Muita RAM usada (>2GB)
├─ Solução: Reduza workers
└─ Execute: python integrar.py -w 3

═════════════════════════════════════════════════════════════════════════════

📊 ESTRUTURA DO CSV FINAL
═════════════════════════════════════════════════════════════════════════════

Coluna          | Exemplo                          | Preenchimento
─────────────────────────────────────────────────────────────────────────
id              | 5e456124dce3db...               | 100% (automático)
titulo          | Apto de 50m² - Centro           | 95% (página)
preco           | R$ 250.000                      | 30% (JSON-LD)
metragem        | 50 m²                           | 25% (regex)
quartos         | 2 Q                             | 20% (regex)
banheiros       | 1 B                             | 20% (regex)
descricao       | Apto bem localizado...          | 10% (meta tags)
endereco        | Rua das Flores, 123             | 5% (JSON-LD)
cidade          | São Paulo                       | 5% (regex)
estado          | SP                              | 5% (regex)
cep             | 01311-100                       | 5% (regex)
contato         | (11) 98765-4321                 | 5% (regex)
link            | https://www.zapimoveis.com.br/... | 100% (banco)
fonte           | ZAPIMOVEIS                      | 100% (banco)
data_coleta     | 2025-11-14T11:32:22             | 100% (sistema)

═════════════════════════════════════════════════════════════════════════════

✅ PRÓXIMAS RODADAS
═════════════════════════════════════════════════════════════════════════════

Para coletar MAIS imóveis (500+), repita:

Rodada 2:
  1. $ python busca_ampla.py "imóvel novo 1"    (3 min)
  2. $ python busca_ampla.py "imóvel novo 2"    (3 min)
  3. $ python integrar.py -w 5                   (15 min)
  4. $ python consolidar.py                      (1 min)
  └─ Total: 22 min, +40 imóveis, 240 total

Rodada 3:
  └─ Repita processo...

═════════════════════════════════════════════════════════════════════════════

Pronto para começar? Execute:

  $ python busca_ampla.py "sua busca aqui"
  
Boa sorte! 🚀

═════════════════════════════════════════════════════════════════════════════
"""
    
    print(guide)


if __name__ == '__main__':
    main()
