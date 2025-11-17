# 🏠 Sistema de Coleta de Imóveis - Pipeline Escalável

Sistema completo para coletar informações de imóveis em grande escala (50k+ propriedades) com preço, localização, CEP, descrição e contato.

## 📊 Fluxo de Funcionamento

### Fase 1: Descoberta de URLs
```bash
python busca_ampla.py "apartamento são paulo"
```
- Busca no Bing usando `site:` commands
- Detecta e espera resolução manual de CAPTCHAs
- Extrai URLs reais de 5 domínios principais
- Salva em `output/imoveis_busca_ampla_*.json` (19 URLs coletadas)

### Fase 2-4: Integração + Processamento + Export
```bash
python integrar.py -w 3 --headless
```
- Lê JSON da Fase 1
- Insere URLs no banco SQLite
- Processa 3 URLs em paralelo (3 workers)
- Extrai dados estruturados (preço, endereço, CEP, telefone)
- Exporta para CSV

### Resultado Final
```
output/imoveis_scraper_escalavel_TIMESTAMP.csv
├─ id (hash único)
├─ titulo (nome do imóvel)
├─ preco (valor em R$)
├─ metragem (m²)
├─ quartos
├─ banheiros
├─ descricao
├─ endereco
├─ cidade
├─ estado
├─ cep
├─ contato (telefone)
├─ link (URL original)
├─ fonte (domínio)
└─ data_coleta
```

## 🗄️ Banco de Dados

SQLite com 3 tabelas:

| Tabela | Função |
|--------|--------|
| `imoveis` | Dados estruturados de imóveis (22 coletados) |
| `links` | URLs para processar (queue) |
| `checkpoint` | Estado de progresso (para retry) |

**Arquivo:** `imoveis.db` (40 KB)

## 🚀 Uso Rápido

### Primeira vez (com CAPTCHA manual)
```bash
# Terminal 1: Descobrir URLs
python busca_ampla.py "apartamento curitiba"
# → Navegador abre, você resolve CAPTCHA manualmente
# → Enter no terminal
# → JSON salvo com 19 URLs

# Terminal 2: Processar URLs → CSV (sem intervenção)
python integrar.py -w 3
# → Lê JSON recente
# → Insere no SQLite
# → Processa com 3 workers
# → Exporta CSV
# → Tempo: ~4 minutos
```

### Verificar resultados
```bash
python stats.py        # Mostrar estatísticas
python resumo.py       # Mostrar arquitetura completa
```

## 📈 Escalar para 50k+ Imóveis

### 1. Múltiplas Buscas (mesma Fase 1)
```bash
python busca_ampla.py "apartamento são paulo"    # ~19 URLs
python busca_ampla.py "casa brasília"            # ~19 URLs
python busca_ampla.py "quarto recife"            # ~19 URLs
# ... repetir para 20-50 keywords
# Resultado: 400-950 URLs totais
```

### 2. Processar todas de uma vez
```bash
python integrar.py -w 5 --skip-search
# Processa todos os JSONs coletados
# Aumenta para 5 workers (mais rápido)
```

### 3. Consolidar CSVs
```python
import pandas as pd
from pathlib import Path

# Concatenar todos os CSVs
csvs = Path('output').glob('imoveis_scraper_escalavel*.csv')
df = pd.concat([pd.read_csv(f) for f in csvs])
df.to_csv('output/imoveis_consolidado.csv', index=False)
print(f"Total de imóveis: {len(df)}")
```

## 🔧 Configurações

Arquivo: `scraper_escalavel.py`

```python
LINKS_PER_DOMAIN = 20      # URLs por domínio em busca_ampla
MAX_WORKERS = 3            # Navegadores paralelos (aumentar = mais rápido, mais RAM)
BATCH_SIZE = 100           # Processar em lotes de 100
RETRY_MAX = 3              # Tentar 3x se falhar
RETRY_BACKOFF_FACTOR = 2   # Esperar 1s, 2s, 4s entre tentativas
```

## 📦 Dependências

```
undetected-chromedriver==3.5.5
selenium==4.38.0
beautifulsoup4
requests
sqlite-utils
tqdm
```

**Instalar:**
```bash
pip install -r requirements.txt
```

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| "CAPTCHA/verification" | Resolveu manualmente? Aperte Enter |
| "Bing is presenting a challenge" | Espera 2s e tenta novamente |
| "Gateway timeout" (OLX/Mercado Livre) | Aumentar timeout (scraper_escalavel.py line 400) |
| CSV vazio | Verificar: `python stats.py` |
| Dados incompletos (sem endereço/CEP) | Site não tem JSON-LD; melhorar regex patterns |

## 📝 Exemplo de Uso Completo (Production)

```bash
#!/bin/bash
# collect_all_properties.sh

keywords=(
    "apartamento são paulo"
    "apartamento rio de janeiro"
    "apartamento belo horizonte"
    "casa brasília"
    "quarto curitiba"
    "casa recife"
)

# FASE 1: Descobrir URLs (manual CAPTCHA)
for kw in "${keywords[@]}"; do
    echo "Buscando: $kw"
    python busca_ampla.py "$kw"
    sleep 5  # esperar para não sobrecarregar
done

# FASE 2-4: Processar tudo
echo "Processando..."
python integrar.py -w 5 --skip-search

# Consolidar
echo "Consolidando CSVs..."
python consolidar_csvs.py

echo "✅ Completo! Ver: output/imoveis_consolidado.csv"
```

## 📊 Performance

| Métrica | Valor |
|---------|-------|
| URLs por keyword | 19 |
| Tempo de busca (1 keyword) | 3-5 min (com CAPTCHA) |
| Tempo de processamento (19 URLs) | 4 min (3 workers) |
| Taxa de sucesso | 100% (17/19 URLs válidas) |
| Dados coletados | 22 imóveis |
| Cobertura de preço | 18% (MercadoLivre tem dados estruturados) |

## 🎯 Roadmap

- [ ] Proxy rotation (evitar CAPTCHA frequente)
- [ ] API fallback (SerpAPI)
- [ ] Scheduler (rodar diariamente)
- [ ] Data warehouse (BigQuery)
- [ ] ML pipeline (classificação de preço)
- [ ] REST API (expor dados)
- [ ] Dashboard (visualizar dados em tempo real)

## 📞 Contato & Suporte

Arquivos principais:
- `busca_ampla.py` - Fase 1 (descoberta)
- `scraper_escalavel.py` - Fases 3-4 (processamento)
- `integrar.py` - Orquestrador
- `stats.py` - Estatísticas
- `imoveis.db` - Banco de dados

---

**v1.0** - Nov 14, 2025
