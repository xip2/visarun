from django.db import connection
from django.shortcuts import render


def countries(request):
    visa_free = request.GET.get("visa_free")
    sea = request.GET.get("sea")  # South-Eastern Asia

    query = """
        SELECT
            oksm.name AS name,
            COALESCE(vr.visa_status, '-') AS visa_status,
            COALESCE(vr.days::text, '-') AS days
        FROM oksm
        LEFT JOIN country_iso ci
            ON ci.country_code = oksm.code
        LEFT JOIN visa_rule vr
            ON vr.name = ci.name
    """

    conditions = []
    params = []

    if visa_free is not None:
        conditions.append("vr.visa_status = %s")
        params.append("visa-free")

    if sea is not None:
        conditions.append("ci.sub_region = %s")
        params.append("South-eastern Asia")

    if request.GET.get("schengen"):
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM oksm_groups og
                WHERE og.country_id = oksm.code
                  AND og.group_id = 65100
            )
        """)

    if conditions:
        query += " WHERE " + " and ".join(conditions)

    query += " ORDER BY oksm.name"

    with connection.cursor() as cursor:
        cursor.execute(query, params)

        columns = [col[0] for col in cursor.description]
        rules = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    template = (
        "countries_table.html"
        if request.headers.get("HX-Request")
        else "countries.html"
    )

    return render(request, template, {"rules": rules})