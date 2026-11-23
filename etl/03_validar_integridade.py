"""Validação de integridade do banco: tipagem, nulos, duplicatas, FKs e regra contábil."""
import sqlite3
import sys

from config import DB_PATH


def checar(con: sqlite3.Connection) -> list[tuple[str, bool, str]]:
    q = lambda sql: con.execute(sql).fetchall()
    res = []

    def teste(nome, ok, detalhe=""):
        res.append((nome, bool(ok), detalhe))

    teste("246 municípios", q("SELECT COUNT(*) FROM municipio")[0][0] == 246)
    teste("12 meses x 246 municípios no ICMS", q("SELECT COUNT(*) FROM repasse_icms_mensal")[0][0] == 12 * 246,
          str(q("SELECT COUNT(*) FROM repasse_icms_mensal")[0][0]))
    teste("1 registro de frota por município", q("SELECT COUNT(*) FROM frota_municipio")[0][0] == 246)
    teste("sem municípios duplicados", q("SELECT COUNT(*)-COUNT(DISTINCT nome) FROM municipio")[0][0] == 0)
    teste("sem duplicatas município x mês",
          q("SELECT COUNT(*) FROM (SELECT 1 FROM repasse_icms_mensal GROUP BY id_municipio, ano_mes HAVING COUNT(*)>1)")[0][0] == 0)
    nulos = q("""SELECT SUM(valor_bruto IS NULL)+SUM(deducao_fundeb IS NULL)+SUM(valor_creditado IS NULL)
                 FROM repasse_icms_mensal""")[0][0]
    teste("sem nulos no ICMS", nulos == 0)
    nulos_f = q("""SELECT SUM(frota_ativa IS NULL)+SUM(passeio IS NULL)+SUM(moto IS NULL)+SUM(carga IS NULL) FROM frota_municipio""")[0][0]
    teste("sem nulos na frota", nulos_f == 0)
    tipos = q("""SELECT DISTINCT typeof(valor_bruto), typeof(valor_creditado), typeof(ano_mes) FROM repasse_icms_mensal""")
    teste("tipagem ICMS (real, real, integer)", tipos == [("real", "real", "integer")], str(tipos))
    tipos_f = q("SELECT DISTINCT typeof(frota_ativa), typeof(moto) FROM frota_municipio")
    teste("tipagem frota (integer)", tipos_f == [("integer", "integer")], str(tipos_f))
    teste("FKs íntegras", len(q("PRAGMA foreign_key_check")) == 0)
    teste("bruto - FUNDEB = creditado (±R$0,02)",
          q("SELECT COUNT(*) FROM repasse_icms_mensal WHERE ABS(valor_bruto-deducao_fundeb-valor_creditado)>0.02")[0][0] == 0)
    teste("frota ativa = soma das categorias",
          q("SELECT COUNT(*) FROM frota_municipio WHERE frota_ativa <> passeio+moto+carga+onibus+outros")[0][0] == 0)
    teste("view analítica com 246 linhas", q("SELECT COUNT(*) FROM vw_analise_municipio")[0][0] == 246)
    teste("todo município com ICMS anual > 0", q("SELECT COUNT(*) FROM vw_analise_municipio WHERE icms_bruto_anual<=0")[0][0] == 0)
    return res


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    resultados = checar(con)
    for nome, ok, det in resultados:
        print(("PASSOU " if ok else "FALHOU ") + nome + (f"  [{det}]" if det and not ok else ""))
    con.close()
    return 0 if all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
