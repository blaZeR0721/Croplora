import logging
import re

from croploraApp.models import PlatformRole, User, OrgRole
from croploraApp.views.utils.helpers import validate_password_strength
from croploraApp.views.utils.redis_client import redis_client
from croploraApp.views.utils.verification import (
    check_resend_allowed, generate_and_send_verification_code)
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from croploraApp.views.utils.choicefields import PlatRoleTypeChoice
from django.core.validators import validate_email
from django.utils import timezone
from rest_framework import serializers

logger = logging.getLogger("croplora")


class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "confirm_password",
        ]
        extra_kwargs = {
            "first_name": {"required": True, "max_length": 150},
            "last_name": {"required": True, "max_length": 150},
            "email": {"required": True},
            "password": {
                "write_only": True,
                "required": True,
                "validators": [validate_password_strength],
            },
        }

    def validate_first_name(self, value):
        name = value.strip()
        if len(name) < 2:
            raise serializers.ValidationError(
                "First name must be at least 2 characters long."
            )
        if not re.match(r"^[a-zA-Z\s]+$", name):
            raise serializers.ValidationError(
                "First name can only contain letters and spaces."
            )
        return name

    def validate_last_name(self, value):
        name = value.strip()
        if len(name) < 1:
            raise serializers.ValidationError("Last name is required.")
        if not re.match(r"^[a-zA-Z\s]+$", name):
            raise serializers.ValidationError(
                "Last name can only contain letters and spaces."
            )
        return name

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        email = validated_data.pop("email").lower().strip()
        password = validated_data.pop("password")
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")

        try:
            plat_role = PlatformRole.objects.get(role_code=PlatRoleTypeChoice.NORMAL_USER)
        except PlatformRole.DoesNotExist:
            raise ValidationError("Issue in getting roles")
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_verified=False,
                organization=None,
                platform_role=plat_role,
            )

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise serializers.ValidationError({"error": "Failed to create user"})

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, style={"input_type": "password"}, write_only=True
    )

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        user = authenticate(username=email, password=password)

        if not user:
            if User.objects.filter(email__iexact=email).exists():
                u = User.objects.filter(email__iexact=email).first()
                if not u.is_active:
                    raise serializers.ValidationError({"error": "Account is disabled."})
                raise serializers.ValidationError({"password": "Incorrect password."})
            raise serializers.ValidationError(
                {"email": "No account found with this email address."}
            )

        if not user.is_active:
            raise serializers.ValidationError({"error": "Account is disabled."})

        attrs["user"] = user
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=6)

    def validate_code(self, value):
        user = self.context["request"].user

        if user.is_verified:
            raise serializers.ValidationError("Email already verified.")

        stored_code = redis_client.get(f"verify:{user.id}")

        if not stored_code:
            raise serializers.ValidationError(
                "No verification code found or code expired."
            )

        if stored_code != value:
            raise serializers.ValidationError("Invalid verification code.")

        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.is_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["is_verified", "email_verified_at"])
        redis_client.delete(f"verify:{user.id}")
        return user


class ResendVerificationCodeSerializer(serializers.Serializer):
    def validate(self, attrs):
        user = self.context["request"].user
        if user.is_verified:
            raise serializers.ValidationError({"error": "Email already verified."})
        if not check_resend_allowed(user):
            raise serializers.ValidationError(
                {"error": "Resend limit reached. Try again in 10 minutes."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        generate_and_send_verification_code(user)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name", read_only=True, allow_null=True
    )
    organization_code = serializers.CharField(
        source="organization.org_code", read_only=True, allow_null=True
    )
    org_role_name = serializers.CharField(
        source="org_role.role_name", read_only=True, allow_null=True
    )
    platform_role_code = serializers.CharField(
        source="platform_role.role_code", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "user_code",
            "email",
            "first_name",
            "last_name",
            "is_verified",
            "email_verified_at",
            "organization",
            "organization_name",
            "organization_code",
            "org_role",
            "org_role_name",
            "platform_role_code",
            "timezone",
            "language_code",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "user_code",
            "email",
            "is_verified",
            "email_verified_at",
            "organization",
            "organization_name",
            "organization_code",
            "org_role",
            "org_role_name",
            "platform_role_code",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
            "date_joined",
            "last_login",
        ]
