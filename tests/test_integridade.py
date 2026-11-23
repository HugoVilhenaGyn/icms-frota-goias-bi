import importlib.util
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("validar", RAIZ / "etl" / "03_validar_integridade.py")


def test_banco_integro():
    import sys
    sys.path.insert(0, str(RAIZ / "etl"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    con = sqlite3.connect(RAIZ / "db" / "icms_frota_goias.db")
    falhas = [n for n, ok, _ in mod.checar(con) if not ok]
    assert not falhas, falhas


def test_resultado_regressao_publicado():
    """Valores citados no relatório (ICMS bruto anual x frota ativa, n = 246)."""
    import sys
    sys.path.insert(0, str(RAIZ))
    import pandas as pd
    from analysis.regressao import ajustar
    df = pd.read_sql("SELECT * FROM vw_analise_municipio", sqlite3.connect(RAIZ / "db" / "icms_frota_goias.db"))
    r = ajustar(df["frota_ativa"], df["icms_bruto_anual"])
    assert round(r.a, 2) == 1152.39 and round(r.b, 2) == 13947925.22 and round(r.r, 4) == 0.9235
