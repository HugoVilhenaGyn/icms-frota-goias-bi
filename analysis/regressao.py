"""Correlação e Regressão Linear Simples (RLS) — Ŷ = b + a·X.

Implementa o cálculo MANUAL (fórmulas de mínimos quadrados) e a conferência com
statsmodels (OLS), usados tanto no relatório quanto no painel.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


@dataclass
class ResultadoRLS:
    n: int
    a: float            # inclinação (variação média de Y por unidade de X)
    b: float            # intercepto
    r: float            # correlação de Pearson
    r2: float
    r2_aj: float
    p_valor_a: float
    ic95_a: tuple[float, float]
    ic95_b: tuple[float, float]
    erro_padrao_resid: float
    spearman: float
    modelo: sm.regression.linear_model.RegressionResultsWrapper

    def equacao(self, y="Ŷ", x="X", casas=2) -> str:
        sinal = "+" if self.a >= 0 else "-"
        return f"{y} = {self.b:,.{casas}f} {sinal} {abs(self.a):,.{casas}f}·{x}"

    def prever(self, x0: float, alpha: float = 0.05) -> dict:
        """Estimativa pontual, IC da média e intervalo de predição individual."""
        pred = self.modelo.get_prediction(np.array([[1.0, x0]])).summary_frame(alpha=alpha)
        return {
            "y_hat": float(pred["mean"].iloc[0]),
            "ic_media": (float(pred["mean_ci_lower"].iloc[0]), float(pred["mean_ci_upper"].iloc[0])),
            "ic_predicao": (float(pred["obs_ci_lower"].iloc[0]), float(pred["obs_ci_upper"].iloc[0])),
        }


def ajustar(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> ResultadoRLS:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(x)
    # --- Fórmulas manuais de mínimos quadrados ---
    sxy = np.sum((x - x.mean()) * (y - y.mean()))
    sxx = np.sum((x - x.mean()) ** 2)
    a_man = sxy / sxx
    b_man = y.mean() - a_man * x.mean()
    # --- statsmodels (OLS) ---
    mod = sm.OLS(y, sm.add_constant(x)).fit()
    b, a = mod.params
    assert np.isclose(a, a_man) and np.isclose(b, b_man), "manual x statsmodels divergem"
    ci = mod.conf_int(alpha=0.05)
    r = float(np.corrcoef(x, y)[0, 1])
    return ResultadoRLS(
        n=n, a=float(a), b=float(b), r=r, r2=float(mod.rsquared), r2_aj=float(mod.rsquared_adj),
        p_valor_a=float(mod.pvalues[1]), ic95_a=(float(ci[1][0]), float(ci[1][1])),
        ic95_b=(float(ci[0][0]), float(ci[0][1])), erro_padrao_resid=float(np.sqrt(mod.scale)),
        spearman=float(stats.spearmanr(x, y)[0]), modelo=mod,
    )


def interpretar_correlacao(r: float) -> str:
    """Classificação verbal da força (convenção usual) e do sentido da correlação."""
    forca = abs(r)
    if forca >= 0.9:
        txt = "muito forte"
    elif forca >= 0.7:
        txt = "forte"
    elif forca >= 0.5:
        txt = "moderada"
    elif forca >= 0.3:
        txt = "fraca"
    else:
        txt = "muito fraca/inexistente"
    sentido = "positiva" if r > 0 else "negativa"
    return f"correlação linear {txt} e {sentido}"
