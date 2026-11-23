"""Executa o pipeline completo: ETL -> carga no banco -> validação de integridade."""
import subprocess
import sys
from pathlib import Path

ETL = Path(__file__).resolve().parent / "etl"
for script in ["01_extrair_transformar.py", "02_carregar_banco.py", "03_validar_integridade.py"]:
    print(f"\n=== {script} ===")
    if subprocess.run([sys.executable, script], cwd=ETL).returncode != 0:
        sys.exit(f"Falha em {script}")
print("\nPipeline concluído. Para abrir o painel: streamlit run app/painel.py")
