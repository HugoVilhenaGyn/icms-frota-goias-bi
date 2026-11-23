"""Configurações centrais do projeto (caminhos e parâmetros)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"
DB_PATH = RAIZ / "db" / "icms_frota_goias.db"
SCHEMA_SQL = RAIZ / "db" / "schema.sql"

ANO_ICMS = 2024            # ano completo de repasses (12 meses)
REF_FROTA = 202501         # foto mensal mais antiga publicada pelo DETRAN-GO
MUNICIPIO_PLACEHOLDER = "MUNICIPIO NAO INFORMADO"  # linha-resíduo da base de repasses
