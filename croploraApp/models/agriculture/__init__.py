from django.core.exceptions import ValidationError
from django.db import models

from ..base import GenericModel
from ...views.utils.choicefields import (
    AddressSourceChoice,
    AreaUnitChoice,
    CropTypeChoice,
)
from ...views.utils.tokenGen import generateRandomCode


class Farm(GenericModel):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="farms",
    )
    farm_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated farm identifier",
    )
    name = models.CharField(max_length=200)
    address = models.OneToOneField(
        "Address",
        on_delete=models.SET_NULL,
        related_name="farm",
        blank=True,
        null=True,
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "farms"
        verbose_name = "Farm"
        verbose_name_plural = "Farms"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_farm_name_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.farm_code})"

    def clean(self):
        super().clean()
        if self.address_id and self.organization_id:
            if self.address.organization_id != self.organization_id:
                raise ValidationError({
                    "address": "Farm address must belong to the same organization."
                })
            if self.address.address_source != AddressSourceChoice.FARM:
                raise ValidationError({
                    "address": "Farm address must use the FARM address source."
                })

    def save(self, *args, **kwargs):
        if not self.farm_code:
            self.farm_code = "FRM" + generateRandomCode(10).upper()
        self.full_clean()
        super().save(*args, **kwargs)


class Crop(GenericModel):
    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="crops",
    )
    crop_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated crop identifier",
    )
    name = models.CharField(max_length=100)
    crop_type = models.CharField(
        max_length=20,
        choices=CropTypeChoice.choices,
    )
    variety = models.CharField(max_length=100, blank=True, default="")
    scientific_name = models.CharField(max_length=150, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "crops"
        verbose_name = "Crop"
        verbose_name_plural = "Crops"
        ordering = ["name", "variety"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name", "variety"],
                name="uniq_crop_name_variety_per_org",
            ),
        ]

    def __str__(self):
        crop_name = f"{self.name} - {self.variety}" if self.variety else self.name
        return f"{crop_name} ({self.crop_code})"

    def save(self, *args, **kwargs):
        if not self.crop_code:
            self.crop_code = "CRP" + generateRandomCode(10).upper()
        self.full_clean()
        super().save(*args, **kwargs)


class Field(GenericModel):
    id = models.BigAutoField(primary_key=True)
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    crop = models.ForeignKey(
        Crop,
        on_delete=models.PROTECT,
        related_name="fields",
        blank=True,
        null=True,
    )
    field_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Auto-generated field identifier",
    )
    name = models.CharField(max_length=150)
    area = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    area_unit = models.CharField(
        max_length=10,
        choices=AreaUnitChoice.choices,
        blank=True,
        null=True,
    )
    is_harvested = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "fields"
        verbose_name = "Field"
        verbose_name_plural = "Fields"
        ordering = ["farm__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "name"],
                name="uniq_field_name_per_farm",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(area__isnull=True, area_unit__isnull=True)
                    | models.Q(area__gt=0, area_unit__isnull=False)
                ),
                name="field_area_unit_pair",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_harvested=False)
                    | models.Q(crop__isnull=False)
                ),
                name="field_harvest_requires_crop",
            ),
        ]

    def clean(self):
        super().clean()
        if self.crop_id and self.farm_id:
            if self.crop.organization_id != self.farm.organization_id:
                raise ValidationError({
                    "crop": "Field crop must belong to the farm's organization."
                })

    def __str__(self):
        return f"{self.name} ({self.field_code}) - {self.farm.name}"

    def save(self, *args, **kwargs):
        if not self.field_code:
            self.field_code = "FLD" + generateRandomCode(10).upper()
        self.full_clean()
        super().save(*args, **kwargs)