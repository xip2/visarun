import csv
from django.core.management.base import BaseCommand
from main.models import Groups


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open("main/data/country_groups.csv", encoding="utf-8") as f:
            reader = csv.reader(f)

            for id, country_id, group_id in reader:
                Groups.objects.create(

                    eu_name=eu_name,
                    name=name
                )