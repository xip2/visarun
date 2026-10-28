from django.db import connection
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse


SORT_COLUMNS = {
    "name": "oksm.name",
    "status": "vr.visa_status",
    "days": "vr.days",
}


# Тестовые карточки безвизового режима.
# Пока подключены для Мьянмы и Армении — чтобы проверить вид на двух странах.
COUNTRY_CARDS = {
    "myanmar": {
        "flag": "main/flags/mm.svg",
        "status": "действует",
        "status_key": "active",
        "rule": "Соглашение о взаимной отмене визовых требований",
        "signed": "28.10.2025",
        "from": "27.01.2026",
        "until": "срок не ограничен",
        "stay": "30 дней за поездку",
        "stay_note": "не более 90 дней в год",
        "capital": "Нейпьидо",
        "religion": "Буддизм (тхеравада)",
        "religion_share": "88%",
        "cities": ["Янгон", "Мандалай", "Нейпьидо", "Моламьяйн", "Баго"],
        "people_note": "перепись 2014 · официальная классификация",
        "ethnic_groups": [
            {"name": "Бирманцы", "share": "68,00 %"},
            {"name": "Шаны", "share": "10,00 %"},
            {"name": "Карены", "share": "7,00 %"},
        ],
        "religions": [
            {"name": "Буддизм", "share": "87,90 %"},
            {"name": "Христианство", "share": "6,20 %"},
            {"name": "Ислам", "share": "4,30 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "0.038348",
            "local_name": "Мьянманский кьят",
            "local_code": "MMK",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 000 MMK = 38,3480 ₽",
        },
        "note": "Подписано 28.10.2025 в Минске. До этого действовал временный безвиз, который продлевали ежегодно.",
        "source_label": "Publication.pravo.gov.ru",
        "source_url": "http://publication.pravo.gov.ru/document/0001202601270001",
    },
    "armenia": {
        "flag": "main/flags/am.svg",
        "status": "действует",
        "status_key": "active",
        "rule": "Соглашение о взаимных безвизовых поездках граждан",
        "signed": "25.09.2000",
        "from": "15.03.2001",
        "until": "срок не ограничен",
        "stay": "180 дней в году",
        "stay_note": "до 30 дней без регистрации",
        "capital": "Ереван",
        "religion": "Христианство (ААЦ)",
        "religion_share": "95%",
        "cities": ["Ереван", "Гюмри", "Ванадзор", "Вагаршапат", "Абовян"],
        "people_note": "перепись 2022",
        "ethnic_groups": [
            {"name": "Армяне", "share": "98,10 %"},
            {"name": "Езиды", "share": "1,10 %"},
            {"name": "Русские", "share": "0,50 %"},
        ],
        "religions": [
            {"name": "Христианство (ААЦ)", "share": "95,20 %"},
            {"name": "Католицизм", "share": "0,60 %"},
            {"name": "Езидизм", "share": "0,50 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "0.22312",
            "local_name": "Армянский драм",
            "local_code": "AMD",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "100 AMD = 22,3120 ₽",
        },
        "note": "Соглашение заключено 25.09.2000, действует в редакции от 18.08.2005. Безвиз — до 180 дней в течение года.",
        "source_label": "Википедия · Армения",
        "source_url": "https://ru.wikipedia.org/wiki/Армения",
    },
}


VISA_STATUS_HELP = [
    (
        "visa-free",
        "Без визы",
        "Виза не нужна: страну можно посещать без предварительного "
        "разрешения. Ограничение по сроку пребывания указано в колонке "
        "«Кол-во дней без визы».",
    ),
    (
        "visa required",
        "Нужна виза",
        "Виза оформляется заранее — в посольстве, консульстве или "
        "визовом центре. Без неё на границу не пустят, даже если есть "
        "обратный билет и бронь отеля.",
    ),
    (
        "eVisa",
        "Электронная виза",
        "Заявка подаётся онлайн на официальном сайте страны. "
        "Разрешение приходит на e-mail, на границе его показывают "
        "распечатанным или на экране телефона. Это полноценная виза, "
        "просто без наклейки в паспорте.",
    ),
    (
        "visa on arrival",
        "Виза по прибытии",
        "Оформляется прямо в аэропорту или на пункте пропуска. "
        "Обычно нужны анкета, фото и оплата сбора; иногда требуется "
        "подтверждение брони отеля и обратный билет.",
    ),
    (
        "eTA",
        "Электронное разрешение на въезд",
        "Electronic Travel Authorization — не виза, а короткая "
        "онлайн-заявка, которая привязывается к паспорту. "
        "Оформляется до поездки, действует несколько лет, "
        "но пребывание в стране ограничено по срокам.",
    ),
    (
        "Arrival Card",
        "Карточка прибытия",
        "Миграционная форма, которую заполняют перед посадкой или "
        "в самолёте. Это не виза и не разрешение на въезд — только "
        "учётные данные о поездке.",
    ),
    (
        "pre-enrollment",
        "Предварительная регистрация",
        "Поездку нужно зарегистрировать на сайте страны до вылета. "
        "Без подтверждения регистрации могут отказать в посадке "
        "или во въезде.",
    ),
    (
        "E-Ticket",
        "Электронный билет",
        "Электронное разрешение или билет, который оформляется "
        "онлайн. Подтверждение предъявляется на границе.",
    ),
    (
        "eVisitors",
        "Электронная регистрация посетителя",
        "Онлайн-анкета перед поездкой, по смыслу близка к eTA: "
        "подтверждение приходит на e-mail и проверяется на границе.",
    ),
    (
        "tourist registration",
        "Туристическая регистрация",
        "Данные о поездке подаются в миграционную службу — "
        "до въезда или сразу после него. Часто делается отелем "
        "или принимающей стороной.",
    ),
    (
        "tourist card",
        "Туристическая карта",
        "Документ или сбор для туристов: оформляется по прибытии "
        "или онлайн, действует ограниченный срок.",
    ),
]


def plural_ru(number, one, few, many):
    """Русская форма множественного числа: 1 страна / 2 страны / 5 стран."""
    number = abs(number) % 100
    if 11 <= number <= 14:
        return many
    number %= 10
    if number == 1:
        return one
    if 2 <= number <= 4:
        return few
    return many


def help_page(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT visa_status, COUNT(*)
            FROM visa_rule
            GROUP BY visa_status
        """)
        counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM oksm")
        countries_total = cursor.fetchone()[0]

    statuses = []
    known = set()

    for key, title, description in VISA_STATUS_HELP:
        known.add(key)
        count = counts.get(key, 0)
        statuses.append({
            "key": key,
            "title": title,
            "description": description,
            "count": count,
            "count_label": (
                f"{count} {plural_ru(count, 'страна', 'страны', 'стран')}"
                if count
                else "нет данных"
            ),
        })

    # Статусы, которых нет в справочнике, показываем без описания,
    # чтобы страница не разошлась с базой.
    extra = sorted(
        (key, count)
        for key, count in counts.items()
        if key and key not in known
    )

    for key, count in extra:
        statuses.append({
            "key": key,
            "title": key,
            "description": "Значение из базы данных, описание пока не добавлено.",
            "count": count,
            "count_label": f"{count} {plural_ru(count, 'страна', 'страны', 'стран')}",
        })

    total = sum(counts.values())

    return render(request, "help.html", {
        "statuses": statuses,
        "total": total,
        "countries_total": countries_total,
        "countries_label": (
            f"{countries_total} "
            f"{plural_ru(countries_total, 'страна', 'страны', 'стран')}"
        ),
    })



def countries(request):

    conditions = []
    params = []

    search = request.GET.get("search")

    sort_key = request.GET.get("sort", "name")
    if sort_key not in SORT_COLUMNS:
        sort_key = "name"

    sort_dir = request.GET.get("dir", "asc")
    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"

    status_filters = [
        ("visa_free", "visa-free"),
        ("evisa", "eVisa"),
        ("eta", "eTA"),
    ]
    status_values = [
        value
        for param, value in status_filters
        if request.GET.get(param)
    ]

    region_filters = [
        ("sea", "sub_region", "South-eastern Asia"),
        ("latam", "sub_region", "Latin America and the Caribbean"),
        ("eastern_europe", "sub_region", "Eastern Europe"),
        ("europe", "region", "Europe"),
    ]
    regions = [
        (field, value)
        for param, field, value in region_filters
        if request.GET.get(param)
    ]

    if status_values:
        placeholders = ", ".join(["%s"] * len(status_values))
        conditions.append(f"vr.visa_status IN ({placeholders})")
        params.extend(status_values)

    if regions:
        region_sql = " OR ".join(
            f"ci.{field} = %s"
            for field, _ in regions
        )
        conditions.append(f"({region_sql})")
        params.extend(value for _, value in regions)

    if request.GET.get("schengen"):
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM oksm_groups og
                WHERE og.country_id = oksm.code
                  AND og.group_id = 65100
            )
        """)

    if request.GET.get("cis"):
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM oksm_groups og
                WHERE og.country_id = oksm.code
                  AND og.group_id = 65517
            )
        """)
    if search:
        search = search.strip()
        if search:
            # Ищем только с начала названия: «Аб» -> Абхазия,
            # а «бха» уже ничего не найдёт. Спецсимволы LIKE экранируем,
            # чтобы % и _ в запросе не превращались в шаблон.
            escaped = (
                search
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            conditions.append("LOWER(oksm.name) LIKE LOWER(%s)")
            params.append(f"{escaped}%")

    query = """
        SELECT
            oksm.name AS name,
            oksm.slug AS slug,
            COALESCE(vr.visa_status, '-') AS visa_status,
            COALESCE(vr.days::text, '-') AS days
        FROM oksm
        LEFT JOIN country_iso ci
            ON ci.oksm_code = oksm.code
        LEFT JOIN visa_rule vr
            ON vr.oksm_code = oksm.code
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    order = f"{SORT_COLUMNS[sort_key]} {sort_dir.upper()} NULLS LAST"
    if sort_key != "name":
        order += ", oksm.name ASC"

    query += " ORDER BY " + order

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

    def sort_url(key):
        query_params = request.GET.copy()
        query_params["sort"] = key
        query_params["dir"] = (
            "desc"
            if sort_key == key and sort_dir == "asc"
            else "asc"
        )
        return "?" + query_params.urlencode()

    context = {
        "rules": rules,
        "sort_key": sort_key,
        "sort_dir": sort_dir,
        "sort_urls": {
            key: sort_url(key)
            for key in SORT_COLUMNS
        },
        "is_htmx": bool(request.headers.get("HX-Request")),
    }

    return render(request, template, context)


def country_detail(request, slug):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                oksm.code,
                oksm.name,
                oksm.slug,
                COALESCE(vr.visa_status, '-') AS visa_status,
                vr.days,
                ci.name AS iso_name,
                ci.alpha_2,
                ci.alpha_3,
                ci.region,
                ci.sub_region
            FROM oksm
            LEFT JOIN country_iso ci
                ON ci.oksm_code = oksm.code
            LEFT JOIN visa_rule vr
                ON vr.oksm_code = oksm.code
            WHERE oksm.slug = %s
        """, [slug])

        row = cursor.fetchone()
        if row is None:
            raise Http404("Страна не найдена")

        columns = [col[0] for col in cursor.description]
        country = dict(zip(columns, row))

        cursor.execute("""
            SELECT g.code, g.eu_name, g.name
            FROM oksm_groups og
            JOIN groups g ON g.code = og.group_id
            WHERE og.country_id = %s
            ORDER BY g.name
        """, [country["code"]])

        columns = [col[0] for col in cursor.description]
        country["groups"] = [
            dict(zip(columns, group))
            for group in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT DISTINCT
                oksm.name AS name,
                oksm.slug AS slug,
                COALESCE(vr.visa_status, '-') AS visa_status
            FROM oksm_groups og
            JOIN oksm ON oksm.code = og.country_id
            LEFT JOIN visa_rule vr ON vr.oksm_code = oksm.code
            WHERE og.group_id IN (
                SELECT group_id FROM oksm_groups WHERE country_id = %s
            )
              AND oksm.code <> %s
            ORDER BY oksm.name
        """, [country["code"], country["code"]])

        columns = [col[0] for col in cursor.description]
        country["neighbours"] = [
            dict(zip(columns, neighbour))
            for neighbour in cursor.fetchall()
        ]

    return render(request, "country_detail.html", {
        "country": country,
        "card": COUNTRY_CARDS.get(slug),
    })


def world_map(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT ON (UPPER(ci.alpha_2))
                UPPER(ci.alpha_2) AS iso,
                oksm.name,
                oksm.slug,
                COALESCE(vr.visa_status, '-') AS visa_status,
                vr.days
            FROM oksm
            JOIN country_iso ci
                ON ci.oksm_code = oksm.code
            LEFT JOIN visa_rule vr
                ON vr.oksm_code = oksm.code
            WHERE ci.alpha_2 IS NOT NULL
              AND oksm.slug IS NOT NULL
            ORDER BY UPPER(ci.alpha_2), oksm.name
        """)
        rows = cursor.fetchall()

    countries = {}
    for iso, name, slug, visa_status, days in rows:
        countries[iso] = {
            "name": name,
            "status": visa_status,
            "days": days,
            "url": reverse("country_detail", args=[slug]),
        }

    return render(request, "map.html", {"map_data": countries})
