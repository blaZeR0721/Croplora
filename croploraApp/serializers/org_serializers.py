import phonenumbers
from croploraApp.models.auth import OrgRole
from croploraApp.models.organization import Organization, OrgUser
from croploraApp.models.reference import Address
from croploraApp.views.utils.choicefields import (AddressSourceChoice,
                                                  OrgRoleTypeChoice)
from django.db import transaction
from rest_framework import serializers

from .common_serializers import AddressSerializer


class OrgCreateUpdateSerializer(serializers.ModelSerializer):

    address = AddressSerializer(write_only=True)

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "address",
            "org_phone_number",
            "website_url",
            "social_media_links",
            "logo",
        )
        read_only_fields = ("id",)

        extra_kwargs = {
            "name": {
                "required": True,
                "allow_blank": False,
                "trim_whitespace": True,
            },
            "address": {
                "required": True,
            },
            "org_phone_number": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
            },
            "website_url": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
            },
            "social_media_links": {
                "required": False,
            },
            "logo": {
                "required": False,
                "allow_null": True,
            },
        }

    def validate_name(self, value):
        value = value.strip()

        queryset = Organization.objects.filter(name__iexact=value)

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An organization with this name already exists."
            )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        prefetched_addresses = getattr(instance, "company_addresses", None)
        if prefetched_addresses is None:
            addr = instance.addresses.filter(
                address_source=AddressSourceChoice.COMPANY
            ).first()
        else:
            addr = prefetched_addresses[0] if prefetched_addresses else None
        data["address"] = AddressSerializer(addr).data if addr else None
        return data

    def validate(self, attrs):
        phone_number = attrs.get(
            "org_phone_number",
            self.instance.org_phone_number if self.instance else None,
        )

        if not phone_number:
            return attrs

        address_data = attrs.get("address")
        if address_data and "country" in address_data:
            country = address_data["country"]
        elif self.instance:
            address = self.instance.addresses.filter(
                address_source=AddressSourceChoice.COMPANY
            ).first()
            country = address.country if address else None
        else:
            country = None

        if not country:
            raise serializers.ValidationError(
                {
                    "address": {
                        "country": (
                            "Country is required to validate "
                            "the organization phone number."
                        )
                    }
                }
            )

        try:
            parsed_number = phonenumbers.parse(
                phone_number,
                country.iso2,
            )

        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(
                {"org_phone_number": ("Enter a valid phone number.")}
            )

        if not phonenumbers.is_valid_number(parsed_number):
            raise serializers.ValidationError(
                {"org_phone_number": ("Enter a valid phone number.")}
            )

        attrs["org_phone_number"] = phonenumbers.format_number(
            parsed_number,
            phonenumbers.PhoneNumberFormat.E164,
        )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        address_data = validated_data.pop("address")

        user = self.context["request"].user

        organization = Organization.objects.create(
            created_by=user,
            **validated_data,
        )

        Address.objects.create(
            organization=organization,
            address_source=AddressSourceChoice.COMPANY,
            **address_data,
        )

        owner_role = OrgRole.objects.get(
            role_code=OrgRoleTypeChoice.OWNER,
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

        user.save(
            update_fields=(
                "organization",
                "org_role",
            )
        )

        return organization

    @transaction.atomic
    def update(self, instance, validated_data):
        address_data = validated_data.pop(
            "address",
            None,
        )

        for field, value in validated_data.items():
            setattr(
                instance,
                field,
                value,
            )

        instance.save()

        if address_data is not None:
            address, _ = Address.objects.get_or_create(
                organization=instance,
                address_source=AddressSourceChoice.COMPANY,
            )

            for field, value in address_data.items():
                setattr(
                    address,
                    field,
                    value,
                )

            address.save()

        return instance
