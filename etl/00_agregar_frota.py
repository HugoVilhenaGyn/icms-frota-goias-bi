"""ETL 0 (opcional) — Agrega a base bruta de frota do DETRAN-GO por município.

Entrada : DA_FROTA_202501.csv (~29 MB, uma linha por município x espécie x cor x
          combustível x situação) baixado de
          https://dadosabertos.go.gov.br/dataset/frota-de-veiculos
Saída   : data/raw/frota_agregada_202501.csv (uma linha por município)

Uso: python etl/00_agregar_frota.py caminho/para/DA_FROTA_202501.csv
"""
import sys
import pandas as pd
from config import RAW

PASSEIO = {"AUTOMOVEL", "CAMINHONETE", "CAMIONETA", "UTILITARIO"}
MOTO = {"MOTOCICLETA", "MOTONETA", "CICLOMOTOR"}
CARGA = {"CAMINHAO", "CAMINHAO TRATOR", "REBOQUE", "SEMI-REBOQUE"}
ONIBUS = {"ONIBUS", "MICROONIB"}


def categoria(especie: str) -> str:
    if especie in PASSEIO:
        return "passeio"
    if especie in MOTO:
        return "moto"
    if especie in CARGA:
        return "carga"
    if especie in ONIBUS:
        return "onibus"
    return "outros"


def main(caminho: str) -> None:
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", dtype={"QTD": "int64"})
    inativa = df[df["SITUACAO"] == "Frota Inativa"].groupby("MUNICIPIO")["QTD"].sum()
    ativa = df[df["SITUACAO"] == "Frota Ativa"].copy()
    ativa["cat"] = ativa["ESPECIE"].map(categoria)
    piv = ativa.pivot_table(index="MUNICIPIO", columns="cat", values="QTD", aggfunc="sum", fill_value=0)
    out = pd.DataFrame({"frota_ativa": ativa.groupby("MUNICIPIO")["QTD"].sum(), "frota_inativa": inativa}).fillna(0)
    for c in ["passeio", "moto", "carga", "onibus"]:
        out[c] = piv.get(c, 0)
    out = out.astype(int).reset_index().rename(columns={"MUNICIPIO": "municipio"}).sort_values("municipio")
    out.to_csv(RAW / "frota_agregada_202501.csv", sep=";", index=False)
    print(f"{len(out)} municípios | frota ativa total = {out['frota_ativa'].sum():,}")


if __name__ == "__main__":
    main(sys.argv[1])
