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
    FARM = 'FARM', 'Farm'
    OTHER = 'OTHER', 'Other'

class CropTypeChoice(models.TextChoices):
    CEREAL = 'CEREAL', 'Cereal'
    PULSE = 'PULSE', 'Pulse'
    OILSEED = 'OILSEED', 'Oilseed'
    VEGETABLE = 'VEGETABLE', 'Vegetable'
    FRUIT = 'FRUIT', 'Fruit'
    FIBER = 'FIBER', 'Fiber'
    CASH = 'CASH', 'Cash crop'
    FODDER = 'FODDER', 'Fodder'
    OTHER = 'OTHER', 'Other'

class AreaUnitChoice(models.TextChoices):
    ACRES = 'ACRES', 'Acres'
    HECTARES = 'HECTARES', 'Hectares'