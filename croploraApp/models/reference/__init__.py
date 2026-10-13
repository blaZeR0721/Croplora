from django.db import models

from ..base import GenericModel
from ...views.utils.choicefields import AddressSourceChoice


class Country(models.Model):
    id = models.BigAutoField(primary_key=True)
    iso2 = models.CharField(max_length=2, unique=True)
    iso3 = models.CharField(max_length=3, unique=True, blank=True, null=True)
    name = models.CharField(max_length=150, unique=True)

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
    code = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=150)

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
        "Organization",
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_source = models.CharField(
        max_length=50,
        choices=AddressSourceChoice.choices,
        default=AddressSourceChoice.OTHER,
        help_text="Type: COMPANY, ORGANIZATION USER, FARM etc.",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="addresses",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name="addresses",
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