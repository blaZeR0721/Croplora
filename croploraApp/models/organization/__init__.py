from django.db import IntegrityError, models
from django.core.validators import RegexValidator

from ..base import GenericModel
from ..reference import Address
from ...views.utils.tokenGen import generateRandomCode, generateRandomNumericCode


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
    org_phone_number = models.CharField(max_length=20, blank=True, null=True)
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
        "OrgRole",
        on_delete=models.SET_NULL,
        related_name="org_users",
        blank=True,
        null=True,
    )
    user = models.OneToOneField(
        "User",
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