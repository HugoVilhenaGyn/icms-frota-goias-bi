"""Painel de BI — ICMS x Frota de veículos nos municípios de Goiás.

Executar:  streamlit run app/painel.py
Todos os dados vêm do banco SQLite (db/icms_frota_goias.db) por consultas SQL em
tempo real — nenhum CSV é lido pelo painel.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from analysis.regressao import ajustar, interpretar_correlacao  # noqa: E402

DB_PATH = RAIZ / "db" / "icms_frota_goias.db"

# Paleta (validada: slots 1 e 2 da paleta categórica de referência) e neutros
AZUL, LARANJA = "#2a78d6", "#eb6834"
CINZA_TXT, CINZA_GRADE = "#52514e", "#e3e2de"

st.set_page_config(page_title="ICMS x Frota — Goiás", page_icon="📊", layout="wide")


# ----------------------------------------------------------------- utilitários
def brl(v: float, casas: int = 2) -> str:
    """Formata em reais no padrão brasileiro: R$ 1.234.567,89."""
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def brl_curto(v: float) -> str:
    if abs(v) >= 1e9:
        return f"R$ {v / 1e9:,.2f} bi".replace(".", ",")
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:,.1f} mi".replace(".", ",")
    return brl(v, 0)


def num(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d3(v: float, casas: int = 3) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def equacao_br(res, y: str = "Ŷ", x: str = "X") -> str:
    sinal = "+" if res.a >= 0 else "−"
    return f"{y} = {num(res.b, 2)} {sinal} {num(abs(res.a), 2)}·{x}"


def titulo(nome: pd.Series) -> pd.Series:
    """'APARECIDA DE GOIANIA' -> 'Aparecida de Goiania' (preposições em minúscula)."""
    t = nome.str.title()
    for prep in ["De", "Do", "Da", "Dos", "Das"]:
        t = t.str.replace(f" {prep} ", f" {prep.lower()} ", regex=False)
    return t


def estilo(fig: go.Figure, titulo: str, h: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color="#0b0b0b"), x=0.0),
        template="plotly_white", height=h, margin=dict(l=10, r=10, t=50, b=10),
        font=dict(color=CINZA_TXT), legend=dict(orientation="h", y=-0.18),
        hoverlabel=dict(bgcolor="white", font_size=12), separators=",.",
    )
    fig.update_xaxes(gridcolor=CINZA_GRADE, zeroline=False)
    fig.update_yaxes(gridcolor=CINZA_GRADE, zeroline=False)
    return fig


# ------------------------------------------------------------------ acesso ao BD
@st.cache_resource
def conexao() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(show_spinner=False)
def consultar(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conexao(), params=params)


SQL_LIMITES = "SELECT MIN(frota_ativa) AS mn, MAX(frota_ativa) AS mx FROM vw_analise_municipio"
SQL_NOMES = "SELECT municipio FROM vw_analise_municipio ORDER BY municipio"


def sql_analise(n_excl: int) -> str:
    excl = f" AND municipio NOT IN ({','.join('?' * n_excl)})" if n_excl else ""
    return ("SELECT municipio, icms_bruto_anual, icms_fundeb_anual, icms_creditado_anual,\n"
            "       frota_ativa, frota_inativa, passeio, moto, carga, onibus, outros\n"
            "FROM   vw_analise_municipio\n"
            f"WHERE  frota_ativa BETWEEN ? AND ?{excl}\n"
            "ORDER  BY municipio")


lim = consultar(SQL_LIMITES).iloc[0]
nomes = consultar(SQL_NOMES)["municipio"].tolist()
MAIORES = ["GOIANIA", "RIO VERDE", "ANAPOLIS"]

# ---------------------------------------------------------------------- filtros
st.sidebar.title("Filtros")
y_op = st.sidebar.radio(
    "Variável resposta (Y)",
    ["ICMS bruto anual", "ICMS creditado (após FUNDEB)"],
    help="Bruto = total repassado antes da dedução do FUNDEB; creditado = valor líquido que entra no caixa do município.",
)
YCOL = "icms_bruto_anual" if y_op == "ICMS bruto anual" else "icms_creditado_anual"
st.sidebar.caption("Variável explicativa (X): **frota ativa de veículos**")
fmin, fmax = st.sidebar.columns(2)
vmin = fmin.number_input("Frota mín.", int(lim.mn), int(lim.mx), int(lim.mn), step=500)
vmax = fmax.number_input("Frota máx.", int(lim.mn), int(lim.mx), int(lim.mx), step=500)
excl_top = st.sidebar.checkbox("Excluir as 3 maiores economias (Goiânia, Rio Verde, Anápolis)",
                               help="Teste de robustez: mostra o quanto a reta depende dos pontos de maior alavancagem.")
excl_extra = st.sidebar.multiselect("Excluir municípios", nomes)
excluidos = tuple(sorted(set(excl_extra) | (set(MAIORES) if excl_top else set())))

sql = sql_analise(len(excluidos))
params = (int(vmin), int(vmax), *excluidos)
df = consultar(sql, params)
st.sidebar.markdown(f"**{len(df)}** de 246 municípios selecionados")
st.sidebar.caption("Fontes: SEFAZ-GO (repasses de ICMS, 2024) e DETRAN-GO (frota, jan/2025) — Portal de Dados Abertos de Goiás.")

st.title("Inteligência Fiscal e Socioeconômica — ICMS x Frota de veículos")
st.caption("Business Intelligence · FATESG · Tecnólogo em Inteligência Artificial")

if len(df) < 3:
    st.warning("Poucos municípios para ajustar a regressão. Amplie os filtros.")
    st.stop()

df["icms_por_veiculo"] = df[YCOL] / df["frota_ativa"]
bins = [0, 2_000, 5_000, 15_000, 50_000, np.inf]
rot = ["< 2 mil", "2–5 mil", "5–15 mil", "15–50 mil", "> 50 mil"]
df["porte"] = pd.cut(df["frota_ativa"], bins=bins, labels=rot, right=False)
res = ajustar(df["frota_ativa"], df[YCOL])

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Municípios", num(len(df)))
k2.metric(y_op, brl_curto(df[YCOL].sum()))
k3.metric("Frota ativa", num(df["frota_ativa"].sum()))
k4.metric("ICMS médio por veículo", brl(df[YCOL].sum() / df["frota_ativa"].sum(), 0))
k5.metric("Correlação (r)", d3(res.r), help=f"R² = {d3(res.r2)}: proporção da variação de Y explicada por X.")

aba1, aba2, aba3, aba4, aba5 = st.tabs(
    ["📊 Visão geral", "📈 Correlação e regressão", "🎯 Simulador preditivo", "🗄️ Banco de dados", "📘 Metodologia"])

# ============================================================== 1) VISÃO GERAL
with aba1:
    log_desc = st.toggle("Escala logarítmica nos gráficos descritivos", value=True,
                         help="ICMS e frota são muito assimétricos: poucos municípios concentram a maior parte.")
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Histogram(x=np.log10(df[YCOL]) if log_desc else df[YCOL], nbinsx=25, marker_color=AZUL,
                                     marker_line=dict(color="white", width=1),
                                     hovertemplate="Faixa: %{x}<br>Municípios: %{y}<extra></extra>"))
        fig.update_xaxes(title="log10(R$) — 6 = 1 milhão, 7 = 10 milhões, 8 = 100 milhões" if log_desc else "R$ por município")
        fig.update_yaxes(title="Nº de municípios")
        st.plotly_chart(estilo(fig, f"Distribuição: {y_op} por município"), width='stretch')
    with c2:
        fig = go.Figure(go.Histogram(x=np.log10(df["frota_ativa"]) if log_desc else df["frota_ativa"], nbinsx=25,
                                     marker_color=AZUL, marker_line=dict(color="white", width=1),
                                     hovertemplate="Faixa: %{x}<br>Municípios: %{y}<extra></extra>"))
        fig.update_xaxes(title="log10(veículos) — 3 = mil, 4 = 10 mil, 5 = 100 mil" if log_desc else "Veículos ativos")
        fig.update_yaxes(title="Nº de municípios")
        st.plotly_chart(estilo(fig, "Distribuição da frota ativa por município"), width='stretch')

    c3, c4 = st.columns(2)
    with c3:
        fig = go.Figure()
        for r_ in rot:
            sub = df[df["porte"] == r_]
            if len(sub):
                fig.add_trace(go.Box(y=sub["icms_por_veiculo"], name=r_, marker_color=AZUL, line=dict(width=1.5),
                                     boxpoints="outliers", text=sub["municipio"],
                                     hovertemplate="%{text}<br>R$ %{y:,.0f} por veículo<extra></extra>"))
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title="Porte do município (frota ativa)")
        fig.update_yaxes(title="R$ de ICMS por veículo ativo", tickformat=",.0f")
        st.plotly_chart(estilo(fig, "ICMS por veículo ativo, por porte do município"), width='stretch')
    with c4:
        top = df.nlargest(10, YCOL).sort_values(YCOL)
        fig = go.Figure(go.Bar(x=top[YCOL], y=titulo(top["municipio"]), orientation="h", marker_color=AZUL,
                               hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>",
                               text=[brl_curto(v) for v in top[YCOL]], textposition="outside", cliponaxis=False))
        fig.update_xaxes(title="R$", range=[0, top[YCOL].max() * 1.22], tickformat=",.0f", nticks=4)
        st.plotly_chart(estilo(fig, "10 maiores municípios em ICMS"), width='stretch')

    top3 = df.nlargest(3, YCOL)
    st.caption(f"Leitura: a distribuição é fortemente assimétrica à direita. Os 3 maiores municípios da seleção "
               f"({', '.join(titulo(top3['municipio']))}) concentram {d3(top3[YCOL].sum() / df[YCOL].sum() * 100, 1)}% do "
               f"{y_op.lower().replace('icms', 'ICMS')} e {d3(top3['frota_ativa'].sum() / df['frota_ativa'].sum() * 100, 1)}% da frota. "
               "Por isso a escala logarítmica ajuda a ver os demais.")

# ====================================================== 2) CORRELAÇÃO E REGRESSÃO
with aba2:
    st.markdown(f"**Modelo:** Y = {y_op} (R$) · X = frota ativa (veículos) · **{equacao_br(res)}**")
    log_sc = st.checkbox("Visualizar em escala logarítmica (a reta continua ajustada em escala linear)", value=False)
    xs = np.linspace(df["frota_ativa"].min(), df["frota_ativa"].max(), 120)
    pred = res.modelo.get_prediction(np.column_stack([np.ones_like(xs), xs])).summary_frame(alpha=0.05)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.r_[xs, xs[::-1]], y=np.r_[pred["mean_ci_upper"], pred["mean_ci_lower"][::-1]],
                             fill="toself", fillcolor="rgba(235,104,52,0.15)", line=dict(width=0),
                             hoverinfo="skip", name="IC 95% da reta"))
    fig.add_trace(go.Scatter(x=df["frota_ativa"], y=df[YCOL], mode="markers", name="Município",
                             marker=dict(color=AZUL, size=8, opacity=0.8, line=dict(color="white", width=1)),
                             text=titulo(df["municipio"]),
                             hovertemplate="<b>%{text}</b><br>Frota: %{x:,.0f}<br>ICMS: R$ %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=xs, y=pred["mean"], mode="lines", name="Reta de regressão (MQO)",
                             line=dict(color=LARANJA, width=3),
                             hovertemplate="Frota: %{x:,.0f}<br>Ŷ: R$ %{y:,.0f}<extra></extra>"))
    for nome_ in MAIORES:  # rótulos diretos seletivos
        linha = df[df["municipio"] == nome_]
        if len(linha):
            fig.add_annotation(x=float(linha["frota_ativa"].iloc[0]), y=float(linha[YCOL].iloc[0]), text=nome_.title(),
                               showarrow=True, arrowhead=0, ax=-35, ay=-22, font=dict(size=11, color=CINZA_TXT),
                               arrowcolor=CINZA_GRADE)
    fig.update_xaxes(title="Frota ativa de veículos (X)", type="log" if log_sc else "linear", tickformat=",.0f")
    fig.update_yaxes(title=f"{y_op} em R$ (Y)", type="log" if log_sc else "linear", tickformat=",.0f")
    st.plotly_chart(estilo(fig, "Dispersão com reta de melhor ajuste (Regressão Linear Simples)", 470), width='stretch')

    m = st.columns([1.6, 1.3, 1, 1, 1.1, 0.7])
    m[0].metric("Inclinação (a)", brl(res.a), help="Variação média do ICMS (R$) para cada veículo ativo a mais.")
    m[1].metric("Intercepto (b)", brl_curto(res.b))
    m[2].metric("Correlação r", f"{res.r:.4f}".replace(".", ","))
    m[3].metric("R²", f"{res.r2:.4f}".replace(".", ","))
    m[4].metric("p-valor (a)", f"{res.p_valor_a:.1e}".replace(".", ","))
    m[5].metric("n", num(res.n))
    st.info(
        f"**Interpretação.** Há {interpretar_correlacao(res.r)} (r = {d3(res.r)}; Spearman = {d3(res.spearman)}). "
        f"O modelo explica {d3(res.r2 * 100, 1)}% da variação do ICMS entre os municípios. Cada veículo ativo a mais "
        f"está associado, em média, a {brl(res.a)} a mais de ICMS (IC 95%: {brl(res.ic95_a[0], 0)} a {brl(res.ic95_a[1], 0)}). "
        "**Correlação não é causalidade:** frota e ICMS crescem juntos porque ambos refletem o tamanho da economia local.")

    d1, d2 = st.columns(2)
    with d1:
        fig = go.Figure(go.Scatter(x=res.modelo.fittedvalues, y=res.modelo.resid, mode="markers",
                                   marker=dict(color=AZUL, size=7, opacity=0.8, line=dict(color="white", width=1)),
                                   text=titulo(df["municipio"]),
                                   hovertemplate="<b>%{text}</b><br>Ajustado: R$ %{x:,.0f}<br>Resíduo: R$ %{y:,.0f}<extra></extra>"))
        fig.add_hline(y=0, line_color=LARANJA, line_width=2)
        fig.update_xaxes(title="Valor ajustado (R$)", tickformat=",.0f")
        fig.update_yaxes(title="Resíduo (R$)", tickformat=",.0f")
        st.plotly_chart(estilo(fig, "Diagnóstico: resíduos x valores ajustados", 360), width='stretch')
        st.caption("A abertura em funil indica variância não constante (heterocedasticidade): o erro cresce com o porte do município.")
    with d2:
        df["esperado"] = res.modelo.fittedvalues
        df["residuo"] = res.modelo.resid
        tab = pd.concat([df.nlargest(5, "residuo"), df.nsmallest(5, "residuo")])[["municipio", YCOL, "esperado", "residuo"]].copy()
        for c_ in [YCOL, "esperado", "residuo"]:
            tab[c_] = tab[c_] / 1e6
        tab["municipio"] = titulo(tab["municipio"])
        tab.columns = ["Município", "Real (R$ mi)", "Esperado (R$ mi)", "Diferença (R$ mi)"]
        st.markdown("**Municípios que mais fogem da reta** (5 acima e 5 abaixo do esperado pela frota)")
        st.dataframe(tab.style.format({"Real (R$ mi)": "{:,.1f}",
                                       "Esperado (R$ mi)": "{:,.1f}", "Diferença (R$ mi)": "{:+,.1f}"}),
                     hide_index=True, width='stretch')
        st.caption("Resíduo positivo: arrecada/recebe mais ICMS do que a frota sugere (ex.: atividade industrial ou comercial forte).")

# ============================================================ 3) SIMULADOR
with aba3:
    st.subheader("Simulador: quanto ICMS a frota sugere?")
    st.markdown(f"Equação ajustada com os filtros atuais: **{equacao_br(res)}**")
    modo = st.radio("Entrada", ["Digitar a frota (X)", "Usar a frota de um município"], horizontal=True)
    cA, cB = st.columns([1, 2])
    real = None
    with cA:
        if modo == "Digitar a frota (X)":
            x0 = st.number_input("Frota ativa de veículos (X)", min_value=0, max_value=2_000_000, value=10_000, step=500)
        else:
            alvo = st.selectbox("Município", df["municipio"].tolist(),
                                index=df["municipio"].tolist().index("GOIANIA") if "GOIANIA" in df["municipio"].values else 0)
            linha = df[df["municipio"] == alvo].iloc[0]
            x0, real = int(linha["frota_ativa"]), float(linha[YCOL])
            st.metric("Frota ativa do município", num(x0))
    p = res.prever(float(x0))
    with cB:
        r1, r2, r3 = st.columns(3)
        r1.metric("Ŷ estimado (ICMS anual)", brl(p["y_hat"], 0))
        r2.metric("ICMS por veículo (estimado)", brl(p["y_hat"] / x0, 0) if x0 else "—")
        if real is not None:
            r3.metric("ICMS real", brl(real, 0), f"{(real / p['y_hat'] - 1) * 100:+.1f}".replace(".", ",") + "% vs. estimado",
                      delta_color="off")
        st.markdown(f"- **IC 95% da média** (para municípios com essa frota): {brl(max(p['ic_media'][0], 0), 0)} a {brl(p['ic_media'][1], 0)}\n"
                    f"- **Intervalo de predição 95%** (para um município individual): {brl(max(p['ic_predicao'][0], 0), 0)} a {brl(p['ic_predicao'][1], 0)}")
    if x0 < df["frota_ativa"].min() or x0 > df["frota_ativa"].max():
        st.warning("⚠️ A frota informada está fora da faixa observada na amostra filtrada: é uma extrapolação, e a previsão é pouco confiável.")
    if p["ic_predicao"][0] < 0:
        st.caption("O limite inferior do intervalo de predição foi truncado em R$ 0 (ICMS não é negativo): sinal de que o modelo linear "
                   "é impreciso para municípios pequenos.")

    xs2 = np.linspace(max(df["frota_ativa"].min(), 1), df["frota_ativa"].max(), 100)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["frota_ativa"], y=df[YCOL], mode="markers", name="Municípios",
                             marker=dict(color=AZUL, size=7, opacity=0.5), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs2, y=res.b + res.a * xs2, mode="lines", name="Reta ajustada", line=dict(color=LARANJA, width=3)))
    fig.add_trace(go.Scatter(x=[x0], y=[p["y_hat"]], mode="markers", name="Sua simulação",
                             marker=dict(color=LARANJA, size=15, symbol="diamond", line=dict(color="white", width=2)),
                             hovertemplate="Frota: %{x:,.0f}<br>Ŷ: R$ %{y:,.0f}<extra></extra>"))
    fig.update_xaxes(title="Frota ativa (X)", tickformat=",.0f")
    fig.update_yaxes(title="ICMS (R$)", tickformat=",.0f")
    st.plotly_chart(estilo(fig, "Onde a simulação cai na reta", 380), width='stretch')

# ============================================================ 4) BANCO DE DADOS
with aba4:
    st.subheader("Banco de dados relacional (SQLite)")
    cc = consultar("""SELECT 'municipio' AS tabela, COUNT(*) AS linhas FROM municipio
                      UNION ALL SELECT 'repasse_icms_mensal', COUNT(*) FROM repasse_icms_mensal
                      UNION ALL SELECT 'frota_municipio', COUNT(*) FROM frota_municipio""")
    cl, cr = st.columns([1, 2])
    with cl:
        st.dataframe(cc, hide_index=True, width='stretch')
        st.code("municipio (1) ──< repasse_icms_mensal (12/mun.)\n"
                "municipio (1) ──< frota_municipio (1/mun.)\n"
                "vw_analise_municipio = JOIN + SUM(ICMS anual)", language="text")
    with cr:
        st.markdown("**Consulta SQL executada agora (parametrizada pelos filtros):**")
        st.code(sql + f"\n-- parâmetros: {params}", language="sql")
    show = df.drop(columns=["porte", "esperado", "residuo"], errors="ignore")
    st.dataframe(show.style.format({c: "{:,.0f}" for c in show.columns if c != "municipio"}),
                 hide_index=True, width='stretch', height=320)
    st.download_button("Baixar dados filtrados (CSV)", show.to_csv(index=False).encode("utf-8"), "icms_frota_filtrado.csv")

# ============================================================ 5) METODOLOGIA
with aba5:
    st.markdown("""
### Problema de negócio
Uma consultoria de inteligência governamental quer saber **se o volume de ICMS repassado aos municípios goianos se relaciona
com o porte da frota de veículos**, um indicador socioeconômico público, e se a frota ajuda a antecipar cenários de arrecadação.

### Variáveis
- **Y (resposta):** ICMS bruto repassado ao município em 2024 (SEFAZ-GO, 12 meses completos).
- **X (explicativa):** frota **ativa** de veículos do município (DETRAN-GO, foto de jan/2025, a mais antiga publicada).

### Modelo
Regressão linear simples por mínimos quadrados: **Ŷ = b + a·X**, com `a = Σ(x−x̄)(y−ȳ) / Σ(x−x̄)²` e `b = ȳ − a·x̄`
(cálculo manual conferido com `statsmodels.OLS` a cada execução).

### Limitações (declare na banca)
1. **Correlação ≠ causalidade.** O ICMS repassado depende do Valor Adicionado Fiscal e de índices legais; a frota é um *proxy* do porte da economia local.
2. **Alavancagem:** Goiânia pesa muito na reta. Use o filtro “Excluir as 3 maiores” para testar a robustez.
3. **Heterocedasticidade e resíduos não normais:** os erros crescem com o porte; os p-valores e intervalos de confiança são aproximados.
4. **Defasagem de um mês:** ICMS de 2024 x frota de jan/2025. A base de frota só começa em jan/2025 e o ICMS de ago–dez/2025 não está publicado com a mesma estrutura.
5. A frota inclui veículos de locadoras e frotistas emplacados no município, o que distorce alguns casos.
""")
