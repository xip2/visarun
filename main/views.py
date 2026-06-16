from django.db import connection
from django.shortcuts import render


def countries(request):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT
            oksm.name AS name,
            COALESCE(vr.visa_status, '-') AS visa_status,
            COALESCE(vr.days::text, '-') AS days
            
        FROM oksm
        LEFT JOIN country_iso ci
            ON ci.country_code = oksm.code
        LEFT JOIN visa_rule vr
            ON vr.name = ci.name
        ORDER BY oksm.name;
        """)

        columns = [col[0] for col in cursor.description]
        rules = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return render(request, "countries.html", {
        "rules": rules
    })