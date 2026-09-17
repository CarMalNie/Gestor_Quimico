"""Permission and ownership tests for compound views and the master-data split."""

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.urls import reverse

from app_quimico.models import Aplicacion, CompuestoAplicacion, CompuestoQuimico, Industria

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
