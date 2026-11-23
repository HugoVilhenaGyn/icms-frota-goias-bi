"""ETL 1 — Extração, limpeza, transformação e cruzamento (pandas + numpy).

Fontes (Portal de Dados Abertos de Goiás):
  * Repasses de impostos aos municípios (SEFAZ-GO) — 12 CSVs mensais de 2024
    https://dadosabertos.go.gov.br/dataset/repasses
  * Frota de veículos (DETRAN-GO) — foto de jan/2025, agregada por município
    https://dadosabertos.go.gov.br/dataset/frota-de-veiculos

Saídas (data/processed/): municipios.csv, repasse_icms_mensal.csv,
frota_municipio.csv e relatorio_qualidade.txt
"""
import glob
import unicodedata

import numpy as np
import pandas as pd

from config import ANO_ICMS, MUNICIPIO_PLACEHOLDER, PROCESSED, RAW, REF_FROTA

log: list[str] = []


def registrar(msg: str) -> None:
    print(msg)
    log.append(msg)


def padronizar_nome(s: pd.Series) -> pd.Series:
    """Caixa alta, sem acentos e sem espaços sobrando (chave de cruzamento)."""
    def limpa(x: str) -> str:
        x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
        return " ".join(x.upper().split())
    return s.map(limpa)


def extrair_icms() -> pd.DataFrame:
    arquivos = sorted(glob.glob(str(RAW / f"icms_{ANO_ICMS}" / "*.csv")))
    assert len(arquivos) == 12, f"esperados 12 arquivos mensais, achei {len(arquivos)}"
    bruto = pd.concat(
        [pd.read_csv(a, sep=";", encoding="utf-8-sig") for a in arquivos], ignore_index=True
    )
    registrar(f"[ICMS] {len(arquivos)} arquivos, {len(bruto):,} linhas brutas")

    # Duplicatas: avaliadas na linha BRUTA completa (datas, IPI e IPVA inclusos).
    # Avaliar só nas colunas de ICMS acusaria falsas duplicatas (linhas de dias em que
    # só houve repasse de IPI/IPVA e o ICMS é 0,00).
    dup = int(bruto.duplicated().sum())
    registrar(f"[ICMS] duplicatas exatas na linha bruta completa = {dup}")
    bruto = bruto.drop_duplicates()

    # Seleciona só o ICMS (a base traz também IPI e IPVA) e renomeia
    df = bruto.rename(columns={
        "NOME_MUNICIPIO": "municipio", "ANO_MES_REPASSE": "ano_mes",
        "VALOR_BRUTO_ICMS": "valor_bruto", "DEDUCAO_FUNDEB_ICMS": "deducao_fundeb",
        "VALOR_CREDITADO_ICMS": "valor_creditado",
    })[["municipio", "ano_mes", "valor_bruto", "deducao_fundeb", "valor_creditado"]]

    df["municipio"] = padronizar_nome(df["municipio"])
    df["ano_mes"] = df["ano_mes"].astype("int64")

    # Remove a linha-resíduo "MUNICIPIO NAO INFORMADO" (só valores zerados)
    resid = df[df["municipio"] == MUNICIPIO_PLACEHOLDER]
    registrar(f"[ICMS] removidas {len(resid):,} linhas '{MUNICIPIO_PLACEHOLDER}' "
              f"(soma do ICMS bruto = R$ {resid['valor_bruto'].sum():,.2f})")
    df = df[df["municipio"] != MUNICIPIO_PLACEHOLDER]

    # Nulos e linhas sem ICMS (dias de repasse só de IPI/IPVA)
    nulos = int(df[["valor_bruto", "deducao_fundeb", "valor_creditado"]].isna().sum().sum())
    registrar(f"[ICMS] nulos nas colunas de ICMS = {nulos}")
    df = df.dropna()
    sem_icms = int((df["valor_bruto"] == 0).sum())
    registrar(f"[ICMS] ignoradas {sem_icms:,} linhas sem ICMS (repasses só de IPI/IPVA, ICMS = 0,00)")
    df = df[df["valor_bruto"] > 0]

    # Regra contábil: bruto - dedução FUNDEB = creditado (tolerância de 1 centavo)
    erro = (df["valor_bruto"] - df["deducao_fundeb"] - df["valor_creditado"]).abs()
    registrar(f"[ICMS] violações de 'bruto - FUNDEB = creditado': {int((erro > 0.01).sum())}")
    assert (df[["valor_bruto", "deducao_fundeb", "valor_creditado"]] >= 0).all().all()

    # Vários repasses por mês (decêndios): consolida em município x mês
    mensal = (
        df.groupby(["municipio", "ano_mes"], as_index=False)
        .agg(valor_bruto=("valor_bruto", "sum"), deducao_fundeb=("deducao_fundeb", "sum"),
             valor_creditado=("valor_creditado", "sum"), qtd_repasses=("valor_bruto", "size"))
    )
    for c in ["valor_bruto", "deducao_fundeb", "valor_creditado"]:
        mensal[c] = np.round(mensal[c], 2)
    registrar(f"[ICMS] consolidado: {len(mensal):,} linhas (município x mês), "
              f"{mensal['municipio'].nunique()} municípios, "
              f"ICMS bruto {ANO_ICMS} = R$ {mensal['valor_bruto'].sum():,.2f}")
    return mensal


def extrair_frota() -> pd.DataFrame:
    df = pd.read_csv(RAW / f"frota_agregada_{REF_FROTA}.csv", sep=";")
    df["municipio"] = padronizar_nome(df["municipio"])
    registrar(f"[FROTA] {len(df)} linhas | duplicatas de município = {int(df['municipio'].duplicated().sum())}"
              f" | nulos = {int(df.isna().sum().sum())}")
    cols = ["frota_ativa", "frota_inativa", "passeio", "moto", "carga", "onibus"]
    df[cols] = df[cols].astype("int64")
    # 'outros' = espécies fora das 4 categorias (tratores, motorcasa, side-car etc.)
    df["outros"] = df["frota_ativa"] - df[["passeio", "moto", "carga", "onibus"]].sum(axis=1)
    assert (df["outros"] >= 0).all(), "categorias somam mais que a frota ativa"
    df["ref_ano_mes"] = REF_FROTA
    return df


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    icms, frota = extrair_icms(), extrair_frota()

    # Cruzamento: chave = nome padronizado do município (granularidade municipal)
    so_icms = sorted(set(icms["municipio"]) - set(frota["municipio"]))
    so_frota = sorted(set(frota["municipio"]) - set(icms["municipio"]))
    registrar(f"[CRUZAMENTO] só no ICMS: {so_icms} | só na frota: {so_frota}")
    comuns = sorted(set(icms["municipio"]) & set(frota["municipio"]))
    registrar(f"[CRUZAMENTO] municípios em comum: {len(comuns)} (Goiás tem 246)")
    assert len(comuns) == 246

    dim = pd.DataFrame({"nome": comuns})
    dim.insert(0, "id_municipio", np.arange(1, len(dim) + 1))
    mapa = dict(zip(dim["nome"], dim["id_municipio"]))

    icms_out = icms.assign(id_municipio=icms["municipio"].map(mapa)).drop(columns="municipio")
    frota_out = frota.assign(id_municipio=frota["municipio"].map(mapa)).drop(columns="municipio")
    icms_out = icms_out[["id_municipio", "ano_mes", "valor_bruto", "deducao_fundeb", "valor_creditado", "qtd_repasses"]]
    frota_out = frota_out[["id_municipio", "ref_ano_mes", "frota_ativa", "frota_inativa",
                           "passeio", "moto", "carga", "onibus", "outros"]]
    assert icms_out["id_municipio"].notna().all() and frota_out["id_municipio"].notna().all()

    dim.to_csv(PROCESSED / "municipios.csv", index=False)
    icms_out.to_csv(PROCESSED / "repasse_icms_mensal.csv", index=False)
    frota_out.to_csv(PROCESSED / "frota_municipio.csv", index=False)
    (PROCESSED / "relatorio_qualidade.txt").write_text("\n".join(log), encoding="utf-8")
    registrar("[OK] CSVs tratados salvos em data/processed/")


if __name__ == "__main__":
    main()
