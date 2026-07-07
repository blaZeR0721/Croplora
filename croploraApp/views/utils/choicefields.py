from django.db import models


class OrgRoleTypeChoice(models.TextChoices):
    OWNER  = "OWNER",  "Organization Owner"
    ADMIN  = "ADMIN",  "Admin"
    WORKER = "WORKER", "Worker"
    CUSTOM = "CUSTOM", "Custom"


class InvitationStatusChoice(models.TextChoices):
    PENDING   = "PENDING",   "Pending"
    ACCEPTED  = "ACCEPTED",  "Accepted"
    EXPIRED   = "EXPIRED",   "Expired"
    CANCELLED = "CANCELLED", "Cancelled"