from django.db import connection
from django.shortcuts import render


def countries(request):
    visa_free = request.GET.get("visa_free")

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

    params = []

    if visa_free is not None:
        query += " WHERE vr.visa_status = %s "
        params.append("visa-free")

    query += " ORDER BY oksm.name "

    with connection.cursor() as cursor:
        cursor.execute(query, params)

        columns = [col[0] for col in cursor.description]
        rules = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    if request.headers.get("HX-Request"):
        return render(
            request,
            "countries_table.html",
            {"rules": rules},
        )

    return render(
        request,
        "countries.html",
        {"rules": rules},
    )