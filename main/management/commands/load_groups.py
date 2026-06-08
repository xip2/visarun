import csv
from django.core.management.base import BaseCommand
from main.models import Groups


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open("main/data/groups.csv", encoding="utf-8") as f:
            reader = csv.reader(f)

            for code, eu_name, name in reader:
                Groups.objects.create(
                    code=code,
                    eu_name=eu_name,
                    name=name
                )