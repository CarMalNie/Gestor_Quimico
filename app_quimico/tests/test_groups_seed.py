"""Seeded default groups are present after migrations."""

from django.contrib.auth.models import Group
from django.test import TestCase


class SeedGroupsTests(TestCase):
    """Fresh test databases must contain all three default groups."""

    def test_default_groups_exist_after_migrations(self):
        for name in ("Quimicos", "Colaboradores", "Administradores"):
            self.assertTrue(
                Group.objects.filter(name=name).exists(),
                f"Group '{name}' should be seeded by migrations",
            )
