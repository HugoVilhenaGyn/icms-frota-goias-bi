# Roteiro de defesa — 15 min de apresentação + 5 min de arguição

Abra antes de começar: terminal na pasta do projeto, `streamlit run app/painel.py` já rodando no navegador, e o VS Code com `etl/01_extrair_transformar.py`, `db/schema.sql` e `analysis/regressao.py` abertos em abas.

## Estrutura (15 min)

| Min | O que mostrar | O que dizer |
|---|---|---|
| 0–1 | Slide/aba do painel (KPIs) | Problema: o ICMS repassado aos 246 municípios se relaciona com o porte da frota? Y = ICMS bruto 2024, X = frota ativa. |
| 1–4 | `etl/01_extrair_transformar.py` + `data/processed/relatorio_qualidade.txt` | Duas fontes do Portal de Dados Abertos. Padronização do nome do município, 246 de 246 casam. Removi 87 linhas de “MUNICIPIO NAO INFORMADO” (ICMS zero), ignorei 7.626 linhas sem ICMS (só IPI/IPVA), consolidei em 2.952 linhas = 246 × 12. Regra contábil bruto − FUNDEB = creditado: 0 violações. |
| 4–6 | `db/schema.sql` + aba “Banco de dados” do painel | SQLite, 3 tabelas + view. PKs compostas impedem duplicata, FKs ativas, CHECK nos valores. `python etl/03_validar_integridade.py`: 14 verificações passam. O painel só lê do banco (mostre a consulta SQL na aba). |
| 6–10 | Aba “Correlação e regressão” | Reta Ŷ = 13.947.925,22 + 1.152,39·X; r = 0,9235; R² = 0,8528. Cada veículo a mais ↔ R$ 1.152 a mais de ICMS. Mostre os resíduos: funil (heterocedasticidade). |
| 10–12 | Marque “Excluir as 3 maiores economias” | A reta muda: r cai para 0,827, inclinação sobe para R$ 1.554. Isto é o que eu **quero** mostrar: conheço os limites do meu modelo. |
| 12–14 | Aba “Simulador” | Digite 10.000 veículos: Ŷ ≈ R$ 25,5 mi. Mostre o intervalo de predição (muito largo para município pequeno). Depois “Usar a frota de um município”: Rio Verde está +R$ 270 mi acima do esperado. |
| 14–15 | Conclusão | Frota é bom indicador de primeira aproximação, não causa o ICMS. Próximo passo: log–log e regressão múltipla. |

## Perguntas prováveis da banca e respostas

**Por que a frota como X?** Proxy do porte econômico local com granularidade municipal e dado público mensal. Não é causal: o ICMS repassado depende do Valor Adicionado Fiscal e de índices legais.

**Por que 2024 e não 2025?** Os arquivos de ago–dez/2025 do portal só trazem IPVA, sem ICMS; 2024 é o último ano com 12 meses completos. A frota só existe a partir de jan/2025, então há defasagem de um mês, que está declarada como limitação.

**Como você calculou a e b?** a = Σ(x−x̄)(y−ȳ)/Σ(x−x̄)², b = ȳ − a·x̄. Está em `analysis/regressao.py`, e o código confere com `statsmodels.OLS` a cada execução (se divergir, o `assert` interrompe).

**O que significa R² = 0,85?** A frota explica 85,3% da variação do ICMS entre municípios; os 14,7% restantes vêm de outros fatores.

**O intercepto de R$ 13,9 milhões faz sentido?** Não literalmente: é o valor para frota zero, e o menor município tem 261 veículos. É um parâmetro de ajuste.

**R² alto significa que o modelo é bom?** Não necessariamente. Goiânia tem distância de Cook de 185; sem ela r cai para 0,873. Breusch-Pagan rejeita variância constante, então p-valores e ICs são aproximados.

**Por que Spearman (0,764) é menor que Pearson (0,923)?** Pearson é puxado pelos poucos municípios gigantes; Spearman usa só a ordem. A relação é forte, mas parte da força vem dos maiores.

**Por que não usou log?** O enunciado pede a reta Ŷ = b + aX em escala natural. O log–log (elasticidade 0,58, R² 0,68) é uma melhoria que deixo como próximo passo.

**O painel lê CSV?** Não. Só consulta o SQLite, com SQL parametrizado pelos filtros (a aba “Banco de dados” exibe a consulta).

**Como foi obtida a frota?** O CSV bruto do DETRAN-GO tem 456 mil linhas; agreguei por município e categoria. Atenção: o `etl/00_agregar_frota.py` foi validado só com amostra sintética; se perguntarem, diga a verdade e, antes da apresentação, rode-o uma vez sobre o `DA_FROTA_202501.csv` oficial (deve dar 3.358.346 veículos ativos e 246 municípios).

**Há duplicatas ou nulos?** Não: 0 duplicatas na linha bruta, 0 nulos no ICMS e na frota, 14 checagens de integridade passando.

## Checklist antes de sair de casa

- [ ] Preencher a equipe na capa do relatório e no anexo de papéis (o .docx está editável).
- [ ] Subir o repositório no GitHub e postar o link + o PDF no Classroom até 23h59.
- [ ] `python run_pipeline.py` e `streamlit run app/painel.py` testados no notebook que vai levar.
- [ ] Rodar `etl/00_agregar_frota.py` sobre o DA_FROTA_202501.csv oficial e conferir o total.
