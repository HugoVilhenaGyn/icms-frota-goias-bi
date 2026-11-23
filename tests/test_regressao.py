import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.regressao import ajustar, interpretar_correlacao  # noqa: E402


def test_reta_exata():
    x = np.arange(1, 21)
    res = ajustar(x, 3 + 2 * x)
    assert res.a == pytest.approx(2) and res.b == pytest.approx(3)
    assert res.r == pytest.approx(1) and res.r2 == pytest.approx(1)


def test_manual_igual_statsmodels():
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 100, 80)
    y = 5 + 1.5 * x + rng.normal(0, 10, 80)
    res = ajustar(x, y)                       # o próprio ajustar() faz assert manual == OLS
    assert res.a == pytest.approx(np.polyfit(x, y, 1)[0])
    assert res.r ** 2 == pytest.approx(res.r2)


def test_predicao_na_media_e_a_media_de_y():
    rng = np.random.default_rng(1)
    x = rng.uniform(0, 50, 60)
    y = 10 + 2 * x + rng.normal(0, 5, 60)
    res = ajustar(x, y)
    assert res.prever(x.mean())["y_hat"] == pytest.approx(y.mean())


def test_interpretacao_textual():
    assert "muito forte" in interpretar_correlacao(0.93)
    assert "negativa" in interpretar_correlacao(-0.4)
