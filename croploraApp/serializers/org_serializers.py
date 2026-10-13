import phonenumbers
from croploraApp.models.auth import OrgRole
from croploraApp.models.organization import Organization, OrgUser
from croploraApp.models.reference import Address
from croploraApp.views.utils.choicefields import (AddressSourceChoice,
                                                  OrgRoleTypeChoice)
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .common_serializers import AddressSerializer


class OwnerDetailsSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=True)
    profile_image = serializers.ImageField(
        required=True,
        allow_null=False,
        allow_empty_file=False,
    )

    class Meta:
        model = OrgUser
        fields = ("phone_number", "address", "profile_image", "date_of_birth")
        extra_kwargs = {
            "phone_number": {
                "required": True,
                "allow_blank": False,
                "trim_whitespace": True,
            },
            "date_of_birth": {
                "required": False,
                "allow_null": True,
            },
        }

    def validate_date_of_birth(self, value):
        if value is not None and value > timezone.localdate():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )
        return value

    def validate(self, attrs):
        address_data = attrs.get("address")
        existing_address = self.instance.address if self.instance else None

        if address_data is None and existing_address is None:
            raise serializers.ValidationError(
                {"address": "Address is required until owner address details are saved."}
            )

        if address_data is not None:
            if existing_address is None:
                missing_fields = {
                    field: "This field is required."
                    for field in ("address_line_1", "country", "state")
                    if field not in address_data
                }
                if missing_fields:
                    raise serializers.ValidationError(
                        {"address": missing_fields}
                    )

            country = address_data.get(
                "country",
                existing_address.country if existing_address else None,
            )
            state = address_data.get(
                "state",
                existing_address.state if existing_address else None,
            )

            if country is None:
                raise serializers.ValidationError(
                    {"address": {"country": "Country is required."}}
                )
            if state is None:
                raise serializers.ValidationError(
                    {"address": {"state": "State is required."}}
                )
            if state.country_id != country.id:
                raise serializers.ValidationError(
                    {
                        "address": {
                            "state": (
                                "The selected state does not belong to the "
                                "selected country."
                            )
                        }
                    }
                )
        else:
            country = existing_address.country

        phone_number = attrs.get("phone_number")
        if phone_number is not None:
            try:
                parsed_number = phonenumbers.parse(phone_number, country.iso2)
            except phonenumbers.NumberParseException:
                raise serializers.ValidationError(
                    {"phone_number": "Enter a valid phone number."}
                )

            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError(
                    {"phone_number": "Enter a valid phone number."}
                )

            attrs["phone_number"] = phonenumbers.format_number(
                parsed_number,
                phonenumbers.PhoneNumberFormat.E164,
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", None)
        old_profile_image_name = (
            instance.profile_image.name
            if "profile_image" in validated_data and instance.profile_image
            else None
        )
        profile_image_storage = instance.profile_image.storage
        update_fields = []
        for field in ("phone_number", "profile_image", "date_of_birth"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                update_fields.append(field)

        if address_data is not None:
            address = instance.address
            if address is None:
                address = Address(
                    organization=instance.organization,
                    address_source=AddressSourceChoice.OWNER,
                )
                instance.address = address
                update_fields.append("address")

            for field, value in address_data.items():
                setattr(address, field, value)

            address.address_source = AddressSourceChoice.OWNER
            address.save()

        if update_fields:
            instance.save(update_fields=(*update_fields, "updated_at"))

        if (
            old_profile_image_name
            and old_profile_image_name != instance.profile_image.name
        ):
            transaction.on_commit(
                lambda: profile_image_storage.delete(old_profile_image_name)
            )

        return instance


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
        addr = self._get_company_address(instance)
        data["address"] = AddressSerializer(addr).data if addr else None
        return data

    def _get_company_address(self, instance):
        prefetched_addresses = getattr(instance, "company_addresses", None)
        if prefetched_addresses is not None:
            return prefetched_addresses[0] if prefetched_addresses else None

        return (
            instance.addresses.filter(address_source=AddressSourceChoice.COMPANY)
            .select_related("country")
            .first()
        )

    def validate(self, attrs):
        address_data = attrs.get("address")
        if address_data is not None:
            existing_address = (
                self._get_company_address(self.instance)
                if self.instance is not None
                else None
            )
            country = address_data.get(
                "country",
                existing_address.country if existing_address else None,
            )
            state = address_data.get(
                "state",
                existing_address.state if existing_address else None,
            )

            if country is None:
                raise serializers.ValidationError(
                    {"address": {"country": "Country is required."}}
                )
            if state is None:
                raise serializers.ValidationError(
                    {"address": {"state": "State is required."}}
                )
            if state.country_id != country.id:
                raise serializers.ValidationError(
                    {
                        "address": {
                            "state": "The selected state does not belong to the selected country."
                        }
                    }
                )

            if existing_address is not None:
                address_data.setdefault("country", existing_address.country)
                address_data.setdefault("state", existing_address.state)

        phone_number = attrs.get(
            "org_phone_number",
            self.instance.org_phone_number if self.instance else None,
        )

        if not phone_number:
            return attrs

        if address_data and "country" in address_data:
            country = address_data["country"]
        elif self.instance:
            address = self._get_company_address(self.instance)
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

        address = Address.objects.create(
            organization=organization,
            address_source=AddressSourceChoice.COMPANY,
            **address_data,
        )
        organization.company_addresses = [address]

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
        old_logo_name = (
            instance.logo.name
            if "logo" in validated_data and instance.logo
            else None
        )
        logo_storage = instance.logo.storage

        for field, value in validated_data.items():
            setattr(
                instance,
                field,
                value,
            )

        instance.save()

        if old_logo_name and old_logo_name != instance.logo.name:
            transaction.on_commit(
                lambda: logo_storage.delete(old_logo_name)
            )

        if address_data is not None:
            address = self._get_company_address(instance)
            if address is None:
                address = Address(
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
            instance.company_addresses = [address]

        return instance
