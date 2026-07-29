from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.text import slugify

from .views.utils.choicefields import (AddressSourceChoice,
                                       InvitationStatusChoice,
                                       OrgRoleTypeChoice, PlatRoleTypeChoice)
from .views.utils.tokenGen import generateRandomCode, generateRandomNumericCode


class GenericModel(models.Model):
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PlatformRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    role_name = models.CharField(max_length=50)
    role_code = models.CharField(
        max_length=20,
        choices=PlatRoleTypeChoice.choices,
        unique=True,
    )
    role_description = models.TextField(blank=True, null=True)
    is_system_role = models.BooleanField(
        default=True,
        help_text="System roles cannot be deleted or modified",
    )

    class Meta:
        db_table = "platform_roles"
        verbose_name = "Platform Role"
        verbose_name_plural = "Platform Roles"
        ordering = ["role_name"]

    def __str__(self):
        return f"{self.role_name} ({self.role_code})"


class OrgRole(models.Model):
    id = models.BigAutoField(primary_key=True)

    role_name = models.CharField(max_length=50, unique=True)
    role_code = models.CharField(
        max_length=20,
        choices=OrgRoleTypeChoice.choices,
        unique=True,
    )

    role_description = models.TextField(blank=True, null=True)

    is_system_role = models.BooleanField(
        default=True,
        help_text="System roles cannot be deleted or modified",
    )

    class Meta:
        db_table = "org_roles"
        verbose_name = "Org Role"
        verbose_name_plural = "Org Roles"
        ordering = ["role_name"]


def org_logo_upload_location(instance, filename):
    return f"organizations/{instance.org_code}/logo/{filename}"


class Organization(GenericModel):

    id = models.BigAutoField(primary_key=True)
    org_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated e.g. ORG00123",
    )
    name = models.CharField(max_length=200)
    org_phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    website_url = models.URLField(max_length=600, blank=True, null=True)
    social_media_links = models.JSONField(default=list, blank=True)
    logo = models.ImageField(
        upload_to=org_logo_upload_location,
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        related_name="organizations_created",
    )
    onboarding_completed = models.BooleanField(default=False)
    onboarded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "organizations"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.org_code})"

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.org_code:
                self.org_code = "ORG" + str(generateRandomNumericCode(5)).zfill(5)

            while True:
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.org_code = "ORG" + str(generateRandomNumericCode(5)).zfill(5)

        super().save(*args, **kwargs)


class Country(models.Model):
    id = models.BigAutoField(primary_key=True)

    iso2 = models.CharField(
        max_length=2,
        unique=True,
    )

    iso3 = models.CharField(
        max_length=3,
        unique=True,
        blank=True,
        null=True,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    class Meta:
        db_table = "countries"
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(models.Model):
    id = models.BigAutoField(primary_key=True)

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="states",
    )

    code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
    )

    name = models.CharField(
        max_length=150,
    )

    class Meta:
        db_table = "states"
        ordering = ["country__name", "name"]
        verbose_name = "State"
        verbose_name_plural = "States"
        unique_together = [
            ("country", "code"),
            ("country", "name"),
        ]

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class Address(GenericModel):
    id = models.BigAutoField(primary_key=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    address_source = models.CharField(
        max_length=50,
        choices=AddressSourceChoice.choices,
        default=AddressSourceChoice.OTHER,
        help_text="Type: COMPANY, ORGANIZATION USER, OWNER etc.",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        related_name="addresses",
        blank=True,
        null=True,
    )

    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        related_name="addresses",
        blank=True,
        null=True,
    )
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)

    postal_code = models.CharField(max_length=20, blank=True, null=True)
    landmark = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = "addresses"
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ["-created_at"]

    def __str__(self):
        state = self.state.name if self.state else ""
        country = self.country.name if self.country else ""
        return f"{self.address_line_1}, {state}, {country}"


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        try:
            extra_fields["platform_role"] = PlatformRole.objects.get(
                role_code="SUPER_ADMIN"
            )
        except PlatformRole.DoesNotExist:
            pass

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):

    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated from email if not provided",
    )
    user_code = models.CharField(
        max_length=15,
        unique=True,
        editable=False,
        help_text="Auto-generated e.g. USR1A2B3C4D",
    )
    email = models.EmailField(unique=True)

    platform_role = models.ForeignKey(
        PlatformRole,
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
    )

    org_role = models.ForeignKey(
        OrgRole,
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
    )

    is_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timezone = models.CharField(max_length=50, default="UTC")
    language_code = models.CharField(max_length=10, default="en")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        role = self.org_role.role_name if self.org_role else "No Role"
        return f"{self.email} ({role})"

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.username:
                base_username = self.email.split("@")[0] if self.email else None
                if base_username:
                    self.username = base_username

            if not self.user_code:
                self.user_code = "USR" + generateRandomCode(8).upper()

            while True:
                try:
                    super().save(*args, **kwargs)
                    return

                except IntegrityError:
                    if User.objects.filter(user_code=self.user_code).exists():
                        self.user_code = "USR" + generateRandomCode(8).upper()
                        continue

                    if User.objects.filter(username=self.username).exists():
                        base_username = self.email.split("@")[0]
                        counter = 1
                        while User.objects.filter(
                            username=f"{base_username}{counter}"
                        ).exists():
                            counter += 1
                        self.username = f"{base_username}{counter}"
                        continue

                    raise

        super().save(*args, **kwargs)

    @property
    def is_org_owner(self):
        return self.org_role and self.org_role.role_type == OrgRoleTypeChoice.OWNER


def org_user_profile_image_upload_location(instance, filename):
    return f"organizations/{instance.organization.org_code}/users/{instance.org_user_code}/profile/{filename}"


class OrgUser(GenericModel):

    id = models.BigAutoField(primary_key=True)
    org_user_code = models.CharField(
        max_length=25,
        editable=False,
        unique=True,
        help_text="Auto-generated e.g. EMP1A2B3C4",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_users",
    )
    address = models.OneToOneField(
        Address,
        on_delete=models.SET_NULL,
        related_name="employee",
        blank=True,
        null=True,
    )
    org_role = models.ForeignKey(
        OrgRole,
        on_delete=models.SET_NULL,
        related_name="org_users",
        blank=True,
        null=True,
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="org_user",
    )
    first_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r"^[a-zA-Z\s\-\.\']+$",
                "Only letters, spaces, hyphens, dots, and apostrophes are allowed.",
            )
        ],
    )
    last_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r"^[a-zA-Z\s\-\.\']+$",
                "Only letters, spaces, hyphens, dots, and apostrophes are allowed.",
            )
        ],
    )
    phone_number = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                r"^[0-9+\-(). ]+$",
                "Only numeric characters and phone symbols are allowed.",
            )
        ],
    )
    profile_image = models.ImageField(
        upload_to=org_user_profile_image_upload_location,
        blank=True,
        null=True,
    )
    date_of_birth = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "org_users"
        verbose_name = "Org User"
        verbose_name_plural = "Org Users"
        ordering = ["organization", "first_name", "last_name"]

    def __str__(self):
        return f"{self.user.email} ({self.org_user_code})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.org_user_code:
            while True:
                self.org_user_code = "EMP" + generateRandomCode(6).upper()
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    continue
        super().save(*args, **kwargs)


class Invitation(GenericModel):

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invitations_sent",
    )
    email = models.EmailField()
    org_role = models.ForeignKey(
        OrgRole,
        on_delete=models.PROTECT,
        related_name="invitations",
        help_text="Role that will be assigned to the user on accepting",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        help_text="Sent in the invite link",
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatusChoice.choices,
        default=InvitationStatusChoice.PENDING,
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_accepted",
    )

    class Meta:
        db_table = "invitations"
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite → {self.email} ({self.organization.name}, {self.status})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Organization.objects.select_for_update().get(pk=self.organization_id)

            if self.status == InvitationStatusChoice.PENDING:
                if (
                    Invitation.objects.filter(
                        organization=self.organization,
                        email=self.email,
                        status=InvitationStatusChoice.PENDING,
                    )
                    .exclude(pk=self.pk)
                    .exists()
                ):
                    raise ValidationError(
                        "A pending invitation already exists for this email in this organization."
                    )

            if not self.pk and not self.token:
                while True:
                    self.token = generateRandomCode(32)
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        continue

            super().save(*args, **kwargs)

    def is_valid(self):
        return (
            self.status == InvitationStatusChoice.PENDING
            and timezone.now() < self.expires_at
        )
