import csv
from django.core.management.base import BaseCommand
from main.models import CountryGroup


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open("main/data/groups.csv", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")

            for code, name in reader:
                CountryGroup.objects.create(
                    code=code,
                    name=name
                )