# Inteligência Fiscal e Socioeconômica com Dados Abertos de Goiás

**ICMS repassado aos municípios × frota de veículos** — ETL, banco de dados, regressão linear simples e painel de BI em Python.

Faculdade SENAI FATESG · Tecnólogo em Inteligência Artificial · Business Intelligence · Prof. Msc. Ujeverson Tavares Sampaio

## Problema de negócio

Uma consultoria de inteligência governamental quer saber se o volume de ICMS repassado aos 246 municípios goianos se relaciona
com o porte da frota de veículos (um indicador socioeconômico público) e se essa relação permite estimar cenários de arrecadação.

| | Variável | Fonte |
|---|---|---|
| **Y** (resposta) | ICMS bruto repassado ao município em **2024** (12 meses completos) | SEFAZ-GO — [Repasses](https://dadosabertos.go.gov.br/dataset/repasses) |
| **X** (explicativa) | Frota **ativa** de veículos do município (foto de **jan/2025**) | DETRAN-GO — [Frota de Veículos](https://dadosabertos.go.gov.br/dataset/frota-de-veiculos) |

## Resultado principal (n = 246 municípios)

```
Ŷ = 13.947.925,22 + 1.152,39 · X          r = 0,9235     R² = 0,8528     p < 10⁻¹⁰²
```

Cada veículo ativo a mais está associado, em média, a **R$ 1.152,39** a mais de ICMS anual (IC 95%: R$ 1.092 a R$ 1.213).
**Ressalvas** (detalhadas no relatório): Goiânia tem influência desproporcional (sem ela, r = 0,873; sem as 3 maiores economias, r = 0,827),
os resíduos são heterocedásticos, e correlação não é causalidade.

## Como executar

Requer Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_pipeline.py          # ETL -> banco SQLite -> validação de integridade (14 verificações)
streamlit run app/painel.py     # abre o painel em http://localhost:8501
python -m pytest -q tests       # testes automatizados (6)
```

O banco já acompanha o repositório populado em `db/icms_frota_goias.db`; o `run_pipeline.py` o recria do zero a partir de `data/raw/`.

## Estrutura

```
data/raw/icms_2024/            12 CSVs mensais de repasses (SEFAZ-GO), sem alteração
data/raw/frota_agregada_202501.csv   frota por município (agregada do CSV bruto do DETRAN-GO)
data/processed/                CSVs tratados + relatorio_qualidade.txt (log da ETL)
etl/00_agregar_frota.py        (opcional) reproduz a agregação a partir do DA_FROTA_202501.csv
etl/01_extrair_transformar.py  limpeza, padronização, cruzamento (pandas + numpy)
etl/02_carregar_banco.py       executa db/schema.sql e carrega os dados
etl/03_validar_integridade.py  tipagem, nulos, duplicatas, FKs, regra contábil
db/schema.sql                  DDL: 3 tabelas, índice e a view vw_analise_municipio
db/icms_frota_goias.db         banco SQLite populado
analysis/regressao.py          RLS manual (mínimos quadrados) conferida com statsmodels
app/painel.py                  painel Streamlit (consultas SQL em tempo real)
tests/                         pytest: regressão e integridade do banco
docs/                          relatório técnico, diagrama do banco, prints do painel, roteiro de defesa
```

## Tratamento de dados (resumo)

- Padronização do nome do município (caixa alta, sem acentos) como chave de cruzamento: **246 de 246** casam.
- Removidas 87 linhas do placeholder `MUNICIPIO NAO INFORMADO` (todas com ICMS = R$ 0,00).
- Ignoradas 7.626 linhas sem ICMS (datas em que só houve repasse de IPI/IPVA); nenhuma duplicata na linha bruta completa.
- Regra contábil verificada em toda a base: `valor bruto − dedução FUNDEB = valor creditado` (0 violações).
- Consolidação dos repasses (4 a 8 por mês) em **município × mês**: 2.952 linhas = 246 × 12.
- ICMS total de 2024 em Goiás: **R$ 7.301.313.516,94**. Frota ativa total: **3.358.346** veículos.

## Decisões e limitações a declarar

1. **Por que 2024 e não 2025?** Nos arquivos mensais de repasses de ago–dez/2025 o portal publica outro esquema (só IPVA, sem ICMS), então 2025 não tem 12 meses de ICMS. O ano de 2024 é o último completo.
2. **Defasagem de um mês:** a série de frota do DETRAN-GO começa em jan/2025; usamos essa foto como estoque de frota ao fim de 2024.
3. **Agregação da frota:** o CSV bruto do DETRAN-GO tem ~29 MB (456 mil linhas). `frota_agregada_202501.csv` é a soma por município e categoria
   (passeio, moto, carga, ônibus, outros), calculada com a mesma regra do script `etl/00_agregar_frota.py`. Na elaboração deste projeto o download
   direto foi bloqueado pelo portal, e a agregação foi feita lendo o CSV pelo navegador; o script foi validado com uma amostra sintética no mesmo esquema,
   mas **recomenda-se rodá-lo uma vez sobre o `DA_FROTA_202501.csv` oficial** para confirmar que reproduz o arquivo agregado (total esperado: 3.358.346 veículos ativos).
4. **Alavancagem e heterocedasticidade:** ver relatório, seção de diagnóstico. O painel permite excluir as maiores economias e ver o efeito na reta.
5. **ICMS não é causado pela frota.** Ambos refletem o tamanho da economia; o repasse depende do Valor Adicionado Fiscal e dos índices legais de participação.
