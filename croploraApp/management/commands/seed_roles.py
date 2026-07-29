from django.core.management.base import BaseCommand

from croploraApp.models import OrgRole, PlatformRole
from croploraApp.views.utils.choicefields import (
    OrgRoleTypeChoice,
    PlatRoleTypeChoice,
)


class Command(BaseCommand):
    help = "Create default platform and organization roles"

    def handle(self, *args, **options):
        self.create_platform_roles()
        self.create_org_roles()

        self.stdout.write(
            self.style.SUCCESS("Default roles created successfully.")
        )

    def create_platform_roles(self):
        for choice in PlatRoleTypeChoice:
            PlatformRole.objects.get_or_create(
                role_code=choice.value,
                defaults={
                    "role_name": choice.label,
                },
            )

    def create_org_roles(self):
        for choice in OrgRoleTypeChoice:
            OrgRole.objects.get_or_create(
                role_code=choice.value,
                defaults={
                    "role_name": choice.label,
                },
            )