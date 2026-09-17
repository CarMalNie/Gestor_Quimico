"""Unit tests for the molecular-weight calculator (no database required)."""

import pytest

from app_quimico.utils import CalculadoraPM

WEIGHTS = {
    "H": 1.008,
    "O": 15.999,
    "C": 12.011,
    "U": 238.029,
    "Cu": 63.546,
    "Ca": 40.078,
    "S": 32.065,
    "Co": 58.933,
    "N": 14.007,
    "Cl": 35.453,
    "Na": 22.990,
}


def _calc(formula):
    return CalculadoraPM(pesos_atomicos=WEIGHTS).analizar_formula(formula)


def test_h2o_pm_y_conteo():
    pm, conteo = _calc("H2O")
    assert pm == pytest.approx(18.015, rel=1e-3)
    assert conteo == {"H": 2, "O": 1}


def test_ca_oh_2():
    pm, conteo = _calc("Ca(OH)2")
    assert pm == pytest.approx(74.092, rel=1e-3)
    assert conteo == {"Ca": 1, "O": 2, "H": 2}


def test_co_nh3_6_cl3():
    pm, conteo = _calc("[Co(NH3)6]Cl3")
    assert pm == pytest.approx(267.478, rel=1e-3)
    assert conteo == {"Co": 1, "N": 6, "H": 18, "Cl": 3}


def test_cu_estricto_iupac():
    pm, conteo = _calc("CU")
    assert pm == pytest.approx(250.040, rel=1e-3)
    assert conteo == {"C": 1, "U": 1}


def test_ho_estricto_iupac():
    pm, conteo = _calc("HO")
    assert pm == pytest.approx(17.007, rel=1e-3)
    assert conteo == {"H": 1, "O": 1}


def test_cu_lowercase_first_rechazado():
    with pytest.raises(ValueError, match="mayúscula"):
        _calc("cU")


def test_h2o_puntuacion_invalida():
    with pytest.raises(ValueError, match="inválida"):
        _calc("H2O!")


def test_uc_lowercase_invalido():
    with pytest.raises(ValueError, match="inválido"):
        _calc("uc")


def test_hidrato_interpunct_rechazado():
    with pytest.raises(ValueError, match="hidrato"):
        _calc("CuSO4·5H2O")


def test_hidrato_punto_rechazado():
    with pytest.raises(ValueError, match="hidrato"):
        _calc("CuSO4.5H2O")


def test_parentesis_sin_cierre():
    with pytest.raises(ValueError, match="grupador"):
        _calc("Ca(OH")


def test_parentesis_extra():
    with pytest.raises(ValueError, match="grupador"):
        _calc("Ca(OH))")


def test_elemento_desconocido_Xx():
    with pytest.raises(ValueError, match="Xx"):
        _calc("Xx")
