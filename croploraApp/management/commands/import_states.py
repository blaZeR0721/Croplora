from pathlib import Path

from croploraApp.models import Country, State
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Import states from GeoNames admin1CodesASCII.txt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to admin1CodesASCII.txt",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        file_path = Path(options["file"])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR("File not found."))
            return

        countries = {country.iso2: country for country in Country.objects.all()}

        states = []

        with open(file_path, encoding="utf-8") as file:

            for line in file:

                columns = line.rstrip("\n").split("\t")

                if len(columns) < 2:
                    continue

                location_code = columns[0]
                state_name = columns[1]

                try:
                    country_code, state_code = location_code.split(".")
                except ValueError:
                    continue

                country = countries.get(country_code)

                if not country:
                    continue

                states.append(
                    State(
                        country=country,
                        code=state_code,
                        name=state_name,
                    )
                )

        State.objects.bulk_create(
            states,
            batch_size=500,
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {len(states)} states.")
        )
