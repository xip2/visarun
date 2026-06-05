import csv
from django.core.management.base import BaseCommand
from main.models import Country


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open("main/data/countries.csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            for code, name in reader:
                Country.objects.create(code=code, name=name)