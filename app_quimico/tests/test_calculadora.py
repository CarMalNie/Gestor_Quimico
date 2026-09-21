"""Unit tests for the molecular-weight calculator (no database required)."""

import pytest

from app_quimico import utils
from app_quimico.services import calcular_pm
from app_quimico.utils import CalculadoraPM

WEIGHTS = {
    "H": 1.008,
    "O": 15.999,
    "C": 12.011,
    "U": 238.029,
    "Cu": 63.546,
    "Ca": 40.078,
    "Fe": 55.845,
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


# --- Hidratos: separador + coeficiente opcional por segmento ---


def test_hidrato_coeficiente_explicito():
    pm, conteo = _calc("CuSO4·5H2O")
    pm_anhidro, conteo_anhidro = _calc("CuSO4")
    pm_agua, conteo_agua = _calc("H2O")
    assert conteo_anhidro == {"Cu": 1, "S": 1, "O": 4}
    assert conteo_agua == {"H": 2, "O": 1}
    assert conteo == {"Cu": 1, "S": 1, "O": 9, "H": 10}
    assert pm == pytest.approx(pm_anhidro + 5 * pm_agua, rel=1e-9)


def test_hidrato_punto_ascii_equivalente():
    pm_interpunct, conteo_interpunct = _calc("CuSO4·5H2O")
    pm_punto, conteo_punto = _calc("CuSO4.5H2O")
    assert conteo_punto == conteo_interpunct
    assert pm_punto == pytest.approx(pm_interpunct, rel=1e-9)


def test_hidrato_coeficiente_implicito_uno():
    pm, conteo = _calc("CuSO4·H2O")
    pm_anhidro, _ = _calc("CuSO4")
    pm_agua, _ = _calc("H2O")
    assert conteo == {"Cu": 1, "S": 1, "O": 5, "H": 2}
    assert pm == pytest.approx(pm_anhidro + pm_agua, rel=1e-9)


def test_hidrato_con_agrupadores():
    pm, conteo = _calc("CuSO4·5(H2O)")
    assert conteo == {"Cu": 1, "S": 1, "O": 9, "H": 10}
    assert pm == pytest.approx(_calc("CuSO4·5H2O")[0], rel=1e-9)


def test_hidrato_anhidro_con_agrupadores_anidados():
    pm, conteo = _calc("Fe(NH4)2(SO4)2·6H2O")
    assert conteo == {"Fe": 1, "N": 2, "H": 20, "S": 2, "O": 14}
    assert pm == pytest.approx(392.135, rel=1e-3)


def test_hidrato_multiples_segmentos():
    pm, conteo = _calc("CuSO4·2H2O·3NH3")
    assert conteo == {"Cu": 1, "S": 1, "O": 6, "H": 13, "N": 3}
    assert pm == pytest.approx(246.730, rel=1e-3)


def test_hidrato_coeficiente_cero_rechazado():
    with pytest.raises(ValueError, match="[Cc]oeficiente de hidrato"):
        _calc("CuSO4·0H2O")


def test_hidrato_segmento_vacio_rechazado():
    with pytest.raises(ValueError, match="[Hh]idrato"):
        _calc("CuSO4·")


def test_hidrato_separador_inicial_rechazado():
    with pytest.raises(ValueError, match="[Hh]idrato"):
        _calc("·5H2O")


def test_hidrato_grupo_desbalanceado_rechazado():
    with pytest.raises(ValueError, match="grupador"):
        _calc("CuSO4·5(H2O")


def test_parentesis_sin_cierre():
    with pytest.raises(ValueError, match="grupador"):
        _calc("Ca(OH")


def test_parentesis_extra():
    with pytest.raises(ValueError, match="grupador"):
        _calc("Ca(OH))")


def test_elemento_desconocido_Xx():
    with pytest.raises(ValueError, match="Xx"):
        _calc("Xx")


def test_subindice_cero_rechazado():
    with pytest.raises(ValueError, match="Subíndice inválido"):
        _calc("H0")


def test_subindice_ceros_multiples_rechazado():
    with pytest.raises(ValueError, match="Subíndice inválido"):
        _calc("Fe00")


def test_subindice_cero_en_grupo_rechazado():
    with pytest.raises(ValueError, match="Subíndice inválido"):
        _calc("Ca(OH)0")


def test_subindice_con_cero_interior_valido():
    # '10' is a valid subscript whose digits include a zero.
    pm, conteo = _calc("H10")
    assert conteo == {"H": 10}
    assert pm == pytest.approx(10.08, rel=1e-3)


# --- calcular_pm service: edge whitespace is tolerated, internal is not ---

# Weight table injected into the process-wide cache so the service can run
# without touching the database; monkeypatch restores the cache afterwards.
_PESOS_SERVICIO = {"Na": 22.990, "Cl": 35.453, "O": 15.999}


@pytest.fixture
def pesos_atomicos_servicio(monkeypatch):
    monkeypatch.setattr(utils, "_cache_pesos", dict(_PESOS_SERVICIO))


def test_calcular_pm_ignora_espacios_en_los_bordes(pesos_atomicos_servicio):
    esperado, _ = calcular_pm("NaClO")
    for formula in ("NaClO ", " NaClO", "  NaClO  "):
        pm, conteo = calcular_pm(formula)
        assert pm == esperado
        assert conteo == {"Na": 1, "Cl": 1, "O": 1}


def test_calcular_pm_rechaza_espacio_interno(pesos_atomicos_servicio):
    with pytest.raises(ValueError, match="no está permitido"):
        calcular_pm("Na ClO")


def test_calcular_pm_rechaza_formula_solo_espacios(pesos_atomicos_servicio):
    with pytest.raises(ValueError, match="vacía"):
        calcular_pm("   ")
