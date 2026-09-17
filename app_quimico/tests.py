"""Permission and ownership tests for compound views and the master-data split."""

import pytest
from decimal import Decimal
from django.contrib.auth.models import Group, Permission, User
from django.urls import reverse

from app_quimico.models import (
    Aplicacion, CompuestoAplicacion, CompuestoQuimico, ElementoQuimico, Industria,
)
from app_quimico.utils import CalculadoraPM

pytestmark = pytest.mark.django_db


@pytest.fixture
def industria():
    return Industria.objects.create(nombre_industria="Farmaceutica")


@pytest.fixture
def aplicacion(industria):
    return Aplicacion.objects.create(id_industria=industria, nombre_uso="Disolvente")


@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="pass12345")


@pytest.fixture
def foreign():
    return User.objects.create_user(username="foreign", password="pass12345")


@pytest.fixture
def own_compound(owner, industria):
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Agua",
        formula_compuesto="H2O",
        id_industria=industria,
        usuario=owner,
        peso_molecular_compuesto="18.0150",
    )


@pytest.fixture
def own_relacion(own_compound, aplicacion):
    return CompuestoAplicacion.objects.create(
        id_compuesto=own_compound,
        id_aplicacion=aplicacion,
        concentracion_minima="10.00",
        tipo_concentracion="%p/p",
    )


@pytest.fixture
def foreign_compound(foreign, industria):
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Metano",
        formula_compuesto="CH4",
        id_industria=industria,
        usuario=foreign,
        peso_molecular_compuesto="16.0430",
    )


# --- Compound ownership ---


def test_list_shows_only_own_compounds(client, owner, own_compound, foreign_compound):
    client.force_login(owner)
    response = client.get(reverse("compuesto_lista"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Agua" in content
    assert "Metano" not in content


def test_owner_can_view_own_compound_detail(client, owner, own_compound, own_relacion):
    """Positive ownership case for DetailView: the owner reads their own compound."""
    client.force_login(owner)
    response = client.get(reverse("compuesto_detalle", kwargs={"pk": own_compound.pk}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Agua" in content
    assert "Disolvente" in content


def test_foreign_compound_detail_returns_404(client, owner, foreign_compound):
    client.force_login(owner)
    response = client.get(reverse("compuesto_detalle", kwargs={"pk": foreign_compound.pk}))
    assert response.status_code == 404


def test_foreign_compound_update_blocked(client, owner, foreign_compound):
    client.force_login(owner)
    response = client.get(reverse("compuesto_actualizar", kwargs={"pk": foreign_compound.pk}))
    assert response.status_code == 403


def test_owner_can_update_own_compound(client, owner, own_compound, own_relacion):
    client.force_login(owner)
    response = client.get(reverse("compuesto_actualizar", kwargs={"pk": own_compound.pk}))
    assert response.status_code == 200


def test_foreign_compound_delete_blocked(client, owner, foreign_compound):
    client.force_login(owner)
    response = client.get(reverse("compuesto_eliminar", kwargs={"pk": foreign_compound.pk}))
    assert response.status_code == 403


def test_owner_can_delete_own_compound(client, owner, own_compound):
    client.force_login(owner)
    response = client.get(reverse("compuesto_eliminar", kwargs={"pk": own_compound.pk}))
    assert response.status_code == 200


# --- Pagination ---


def test_compound_list_paginates_by_twelve(client, owner, industria):
    for i in range(13):
        CompuestoQuimico.objects.create(
            nombre_compuesto=f"Compuesto {i:02d}",
            formula_compuesto=f"H{i}",
            id_industria=industria,
            usuario=owner,
            peso_molecular_compuesto="18.0150",
        )
    client.force_login(owner)

    page_one = client.get(reverse("compuesto_lista"))
    assert page_one.context["is_paginated"] is True
    assert len(page_one.context["compuestos"]) == 12
    assert "Compuesto 12" not in page_one.content.decode()

    page_two = client.get(reverse("compuesto_lista"), {"page": 2})
    assert len(page_two.context["compuestos"]) == 1
    assert "Compuesto 12" in page_two.content.decode()


# --- Master-data permission split ---


def test_colaborador_can_access_industria_create(client):
    group = Group.objects.create(name="Colaboradores")
    add_perm = Permission.objects.get(
        codename="add_industria", content_type__app_label="app_quimico"
    )
    change_perm = Permission.objects.get(
        codename="change_industria", content_type__app_label="app_quimico"
    )
    group.permissions.add(add_perm, change_perm)
    user = User.objects.create_user(username="colab", password="pass12345")
    user.groups.add(group)
    client.force_login(user)
    response = client.get(reverse("industria_crear"))
    assert response.status_code == 200


def test_plain_user_cannot_access_industria_create(client):
    user = User.objects.create_user(username="plain", password="pass12345")
    client.force_login(user)
    response = client.get(reverse("industria_crear"))
    assert response.status_code == 403


# --- Weight cache invalidation ---


def test_weight_cache_serves_updated_atomic_weight():
    """Updating an element row must be picked up by the next calculation
    (post_save signal drops the per-process cache)."""
    ElementoQuimico.objects.create(
        nombre_elemento="Francio",
        simbolo_elemento="Fr",
        numero_atomico_elemento=87,
        peso_atomico_elemento=Decimal("223.0000"),
    )
    pm_inicial, _ = CalculadoraPM().analizar_formula("Fr2")
    assert pm_inicial == pytest.approx(446.0, rel=1e-4)

    elemento = ElementoQuimico.objects.get(simbolo_elemento="Fr")
    elemento.peso_atomico_elemento = Decimal("225.0000")
    elemento.save()

    pm_actualizado, _ = CalculadoraPM().analizar_formula("Fr2")
    assert pm_actualizado == pytest.approx(450.0, rel=1e-4)


def test_weight_cache_serves_deleted_element_after_reload():
    """After deleting an element, the stale cache must not keep serving its weight."""
    elemento = ElementoQuimico.objects.create(
        nombre_elemento="Cesio",
        simbolo_elemento="Cs",
        numero_atomico_elemento=55,
        peso_atomico_elemento=Decimal("132.9054"),
    )
    pm_inicial, _ = CalculadoraPM().analizar_formula("Cs")
    assert pm_inicial == pytest.approx(132.9054, rel=1e-4)

    elemento.delete()

    with pytest.raises(ValueError, match="Símbolo no reconocido"):
        CalculadoraPM().analizar_formula("Cs")
