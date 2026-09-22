"""Client-level regression tests for editing a compound's molecular weight.

Bug (PA production, 2026-09-21): editing a compound from CuSO4 5H2O to CuSO4
did not change the stored PM (it stayed 249.6770). Root cause was in
``CompuestoUpdateView.post``: the bound ``CompuestoQuimicoForm`` receives the
persistent instance, and ``ModelForm.is_valid()`` mutates it in place through
``_post_clean``/``construct_instance`` (``save(commit=False)`` mutates it too).
Reading ``compuesto.formula_compuesto`` after validation therefore returned the
NEW POST value, making ``debe_recalcular`` always False whenever a PM was
already stored. The fix captures the original formula before the form is
validated.

Login goes through HTTP POST to the login route because django-axes rejects the
direct ``client.login()`` helper (same pattern as ``test_force_mfa.py``).
"""

from decimal import Decimal

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from app_quimico.models import (
    Aplicacion,
    CompuestoAplicacion,
    CompuestoQuimico,
    ElementoCompuesto,
    Industria,
)
from app_quimico.services import calcular_pm, registrar_elementos_compuesto

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
FORMULA_HIDRATO = "CuSO4·5H2O"
FORMULA_ANHIDRA = "CuSO4"


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="owner_pm", password=PASSWORD, email="owner_pm@correo.com"
    )


@pytest.fixture
def industria():
    # Data migrations 0007/0008 seed the master tables, so reuse any existing
    # row instead of creating a colliding duplicate (MySQL collation is
    # case-insensitive on the unique name).
    return Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]


@pytest.fixture
def aplicacion(industria):
    return Aplicacion.objects.get_or_create(
        id_industria=industria, nombre_uso="Uso Regresión PM"
    )[0]


@pytest.fixture
def compuesto(owner, industria):
    """A saved hydrate whose PM and element rows are already persisted."""
    call_command("cargar_elementos")

    peso, conteo = calcular_pm(FORMULA_HIDRATO)
    compuesto = CompuestoQuimico.objects.create(
        nombre_compuesto="Sulfato de cobre(II) pentahidratado",
        formula_compuesto=FORMULA_HIDRATO,
        id_industria=industria,
        usuario=owner,
        peso_molecular_compuesto=peso,
    )
    registrar_elementos_compuesto(compuesto, conteo)
    return compuesto


@pytest.fixture
def relacion(compuesto, aplicacion):
    return CompuestoAplicacion.objects.create(
        id_compuesto=compuesto,
        id_aplicacion=aplicacion,
        concentracion_minima=Decimal("10.00"),
        tipo_concentracion="%p/p",
    )


def _login(client, user):
    return client.post(
        reverse("login"),
        data={"username": user.username, "password": PASSWORD},
    )


def _post_update(client, compuesto, industria, aplicacion, formula):
    return client.post(
        reverse("compuesto_actualizar", kwargs={"pk": compuesto.pk}),
        data={
            "nombre_compuesto": compuesto.nombre_compuesto,
            "formula_compuesto": formula,
            "tipo_industria": industria.pk,
            "id_aplicacion": aplicacion.pk,
            "concentracion_minima": "10.00",
            "tipo_concentracion": "%p/p",
        },
        follow=True,
    )


def _elementos_por_simbolo(compuesto):
    return {
        fila.id_elemento.simbolo_elemento: fila.cantidad_elem_en_comp
        for fila in ElementoCompuesto.objects.filter(id_compuesto=compuesto)
    }


# --- Recalculate when the formula actually changed ---


def test_changed_formula_recalculates_pm_and_elements(
    client, owner, industria, aplicacion, compuesto, relacion
):
    """Editing the hydrate to its anhydrous form must refresh PM and rows."""
    _login(client, owner)

    response = _post_update(
        client, compuesto, industria, aplicacion, FORMULA_ANHIDRA
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto.refresh_from_db()
    assert compuesto.formula_compuesto == FORMULA_ANHIDRA

    peso_esperado, _ = calcular_pm(FORMULA_ANHIDRA)
    assert float(compuesto.peso_molecular_compuesto) == pytest.approx(
        float(peso_esperado), abs=0.01
    )

    elementos = _elementos_por_simbolo(compuesto)
    assert elementos == {"Cu": 1, "S": 1, "O": 4}
    assert "H" not in elementos


# --- Do NOT recalculate when the formula is unchanged ---


def test_unchanged_formula_keeps_stored_pm_and_elements(
    client, owner, industria, aplicacion, compuesto, relacion
):
    """A no-op edit must skip recalculation, preserving stored values.

    A sentinel PM proves the stored value was not overwritten, and the
    surviving H row proves ElementoCompuesto was not rewritten.
    """
    sentinel = Decimal("999.0000")
    compuesto.peso_molecular_compuesto = sentinel
    compuesto.save(update_fields=["peso_molecular_compuesto"])

    _login(client, owner)

    response = _post_update(
        client, compuesto, industria, aplicacion, FORMULA_HIDRATO
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto.refresh_from_db()
    assert compuesto.formula_compuesto == FORMULA_HIDRATO
    assert compuesto.peso_molecular_compuesto == sentinel

    elementos = _elementos_por_simbolo(compuesto)
    assert elementos == {"Cu": 1, "S": 1, "O": 9, "H": 10}
