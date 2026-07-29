from django.db import models


class OrgRoleTypeChoice(models.TextChoices):
    OWNER  = "OWNER",  "Organization Owner"
    ADMIN  = "ADMIN",  "Admin"
    WORKER = "WORKER", "Worker"

class PlatRoleTypeChoice(models.TextChoices):
    NORMAL_USER = "NORMAL_USER","Normal User"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    
class InvitationStatusChoice(models.TextChoices):
    PENDING   = "PENDING",   "Pending"
    ACCEPTED  = "ACCEPTED",  "Accepted"
    EXPIRED   = "EXPIRED",   "Expired"
    CANCELLED = "CANCELLED", "Cancelled"

class AddressSourceChoice(models.TextChoices):
    COMPANY = 'COMPANY', 'Company'
    USER = 'ORG_USER', 'Organization User'
    OWNER = 'OWNER', 'Owner'
    OTHER = 'OTHER', 'Other'