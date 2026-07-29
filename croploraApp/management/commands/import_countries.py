from pathlib import Path

from croploraApp.models import Country
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Import countries from GeoNames countryInfo.txt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to countryInfo.txt",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR("File not found."))
            return

        countries = []

        with open(file_path, encoding="utf-8") as file:
            for line in file:

                if line.startswith("#"):
                    continue

                columns = line.rstrip("\n").split("\t")

                if columns[0] == "ISO":
                    continue

                countries.append(
                    Country(
                        iso2=columns[0],
                        iso3=columns[1],
                        name=columns[4],
                    )
                )

        Country.objects.bulk_create(
            countries,
            batch_size=500,
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {len(countries)} countries.")
        )
