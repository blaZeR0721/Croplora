from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.db import IntegrityError


from .views.utils.choicefields import InvitationStatusChoice, OrgRoleTypeChoice
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
        unique=True,
        help_text="e.g. SUPER_ADMIN, NORMAL_USER",
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
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text="Auto-generated from name",
    )
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
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=10, default="INR")
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
        if not self.pk and not self.org_code:
            self.org_code = "ORG" + str(generateRandomNumericCode(5)).zfill(5)
            while Organization.objects.filter(org_code=self.org_code).exists():
                self.org_code = "ORG" + str(generateRandomNumericCode(5)).zfill(5)

        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while (
                Organization.objects.filter(slug=self.slug).exclude(pk=self.pk).exists()
            ):
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)


class OrgRole(models.Model):

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_roles",
    )
    role_name = models.CharField(max_length=50)
    role_code = models.CharField(
        max_length=20,
        blank=True,
        editable=False,
        help_text="Auto-generated unique role code per org",
    )
    role_type = models.CharField(
        max_length=20,
        choices=OrgRoleTypeChoice.choices,
        help_text="OWNER / ADMIN / WORKER / CUSTOM",
    )
    role_description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Default roles cannot be edited or deleted",
    )

    class Meta:
        db_table = "org_roles"
        verbose_name = "Org Role"
        verbose_name_plural = "Org Roles"
        unique_together = [["organization", "role_name"], ["organization", "role_code"]]
        ordering = ["organization", "role_name"]

    def __str__(self):
        return f"{self.organization.name} - {self.role_name} ({self.role_code})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.role_code:
            self.role_code = generateRandomCode(8).upper()
            while OrgRole.objects.filter(
                organization=self.organization,
                role_code=self.role_code,
            ).exists():
                self.role_code = generateRandomCode(8).upper()
        super().save(*args, **kwargs)


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

    from django.db import IntegrityError

    def save(self, *args, **kwargs):
        if not self.username:
            base_username = self.email.split("@")[0] if self.email else None
            if base_username:
                self.username = base_username
                counter = 1
                while (
                    User.objects.filter(username=self.username)
                    .exclude(pk=self.pk)
                    .exists()
                ):
                    self.username = f"{base_username}{counter}"
                    counter += 1

        if not self.pk and not self.user_code:
            while True:
                self.user_code = "USR" + generateRandomCode(8).upper()
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    continue

        super().save(*args, **kwargs)

    @property
    def is_org_owner(self):
        return self.org_role and self.org_role.role_type == OrgRoleTypeChoice.OWNER

    @property
    def display_name(self):
        if hasattr(self, "org_user"):
            return self.org_user.full_name
        return self.email


def org_user_profile_image_upload_location(instance, filename):
    return f"organizations/{instance.organization.org_code}/users/{instance.org_user_code}/profile/{filename}"


class OrgUser(GenericModel):

    id = models.BigAutoField(primary_key=True)
    org_user_code = models.CharField(
        max_length=25,
        editable=False,
        help_text="Auto-generated e.g. EMP1A2B3C4",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_users",
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
        unique_together = [["organization", "org_user_code"]]
        ordering = ["organization", "first_name", "last_name"]


    def __str__(self):
        return f"{self.full_name} ({self.org_user_code})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.org_user_code:
            self.org_user_code = "EMP" + generateRandomCode(6).upper()
            while OrgUser.objects.filter(
                organization=self.organization,
                org_user_code=self.org_user_code,
            ).exists():
                self.org_user_code = "EMP" + generateRandomCode(6).upper()
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
        if not self.pk and not self.token:
            self.token = generateRandomCode(32)
            while Invitation.objects.filter(token=self.token).exists():
                self.token = generateRandomCode(32)
        super().save(*args, **kwargs)

    def is_valid(self):
        return (
            self.status == InvitationStatusChoice.PENDING
            and timezone.now() < self.expires_at
        )


class PasswordResetToken(GenericModel):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reset token for {self.user.email} ({'used' if self.is_used else 'active'})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.token:
            self.token = generateRandomCode(32)
            while PasswordResetToken.objects.filter(token=self.token).exists():
                self.token = generateRandomCode(32)
        super().save(*args, **kwargs)

    def is_valid(self):
        return (not self.is_used) and timezone.now() < self.expires_at


DEFAULT_ORG_ROLES = [
    (OrgRoleTypeChoice.OWNER, "Organization Owner", True),
    (OrgRoleTypeChoice.ADMIN, "Admin", True),
    (OrgRoleTypeChoice.WORKER, "Worker", True),
]


def create_default_org_roles(organization):
    roles = {}
    for role_type, role_name, is_default in DEFAULT_ORG_ROLES:
        role, _ = OrgRole.objects.get_or_create(
            organization=organization,
            role_type=role_type,
            defaults={
                "role_name": role_name,
                "is_default": is_default,
            },
        )
        roles[role_type] = role
    return roles
