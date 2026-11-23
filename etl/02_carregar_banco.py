"""ETL 2 — Cria o banco SQLite (DDL) e carrega integralmente os dados tratados."""
import sqlite3

import pandas as pd

from config import DB_PATH, PROCESSED, SCHEMA_SQL


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()                      # recarga completa e idempotente
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))   # cria tabelas, índices e view

    for tabela, arq in [("municipio", "municipios.csv"),
                        ("repasse_icms_mensal", "repasse_icms_mensal.csv"),
                        ("frota_municipio", "frota_municipio.csv")]:
        df = pd.read_csv(PROCESSED / arq)
        df = df.rename(columns={"nome": "nome"})
        df.to_sql(tabela, con, if_exists="append", index=False)   # respeita tipos/CHECKs do DDL
        print(f"{tabela}: {len(df):,} linhas carregadas")

    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"Banco criado em {DB_PATH}")


if __name__ == "__main__":
    main()
