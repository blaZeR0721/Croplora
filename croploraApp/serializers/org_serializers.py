import logging

from croploraApp.models import Address, Organization, OrgRole, OrgUser
from croploraApp.views.utils.choicefields import (AddressSourceChoice,
                                                  OrgRoleTypeChoice)
from django.db import transaction
from rest_framework import serializers

from .common_serializers import AddressSerializer

logger = logging.getLogger("croplora")


class OrgCreateSerializer(serializers.ModelSerializer):
    address = AddressSerializer()

    class Meta:
        model = Organization
        fields = (
            "name",
            "address",
            "org_phone_number",
            "website_url",
            "social_media_links",
            "logo",
        )

    @transaction.atomic
    def create(self, validated_data):
        address_data = validated_data.pop("address")
        user = self.context["request"].user

        try:
            organization = Organization.objects.create(
                created_by=user, **validated_data
            )

            Address.objects.create(
                organization=organization,
                address_source=AddressSourceChoice.COMPANY,
                **address_data,
            )

            owner_role = OrgRole.objects.get(
                role_type=OrgRoleTypeChoice.OWNER,
            )

            OrgUser.objects.create(
                organization=organization,
                user=user,
                org_role=owner_role,
                first_name=user.first_name,
                last_name=user.last_name,
            )

            user.organization = organization
            user.org_role = owner_role
            user.save(update_fields=("organization", "org_role"))

            return organization

        except Exception:
            logger.exception("Failed to create organization.")
            raise serializers.ValidationError(
                {"detail": "Unable to create organization. Please try again."}
            )
