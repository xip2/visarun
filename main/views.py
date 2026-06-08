from django.shortcuts import render
from main.models import Country


def countries(request):
    rules = Country.objects.prefetch_related("groups").all()

    for r in rules:
        r.group_names = ", ".join(g.name for g in r.groups.all())

    return render(request, "countries.html", {
        "rules": rules
    })