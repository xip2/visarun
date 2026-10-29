import json
import re
from pathlib import Path

from django.db import connection
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse


SORT_COLUMNS = {
    "name": "oksm.name",
    "status": "vr.visa_status",
    "days": "vr.days",
}


# Алиасы для поиска в поле «Поиск страны».
# Ключ — точное название страны из таблицы oksm,
# список — как страну могут набирать в поиске.
# Поиск идёт по префиксу: запрос должен совпадать с началом
# алиаса (например «США» -> «США», «амер» -> «Америка») или начинаться
# с алиаса целиком («соединенные штаты америки» -> «Соединенные Штаты»).
# Нормализация ё->е общая, алиасы пишем через «е», как в базе.
COUNTRY_SEARCH_ALIASES = {
    "Соединенные Штаты": [
        "США",
        "Соединенные Штаты Америки",
        "Америка",
        "Штаты",
        "USA",
        "US",
    ],
    "Соединенное Королевство": [
        "Великобритания",
        "Англия",
        "Британия",
        "UK",
        "GB",
    ],
    "Объединенные Арабские Эмираты": [
        "ОАЭ",
        "Эмираты",
        "Дубай",
    ],
    "Корея, Республика": [
        "Южная Корея",
        "Корея",
    ],
    "Корея, Народно-Демократическая Республика": [
        "Северная Корея",
        "КНДР",
    ],
    "Сирийская Арабская Республика": [
        "Сирия",
    ],
    "Лаосская Народно-Демократическая Республика": [
        "Лаос",
    ],
    # ⚠️ в данных название с лишним «1» на конце (countries.csv, строка 233).
    # Если поправишь данные и перезальёшь базу — обнови ключ здесь.
    "Республика Македония1": [
        "Северная Македония",
        "Македония",
    ],
    "Киргизия": [
        "Кыргызстан",
        "Кыргызская Республика",
    ],
    "Нидерланды": [
        "Голландия",
    ],
    "Кабо-Верде": [
        "Зеленого Мыса",
        "Зеленый Мыс",
    ],
    # В базе название с обратным апострофом: «Кот д`Ивуар».
    "Кот д`Ивуар": [
        "Берег Слоновой Кости",
        "Кот-д'Ивуар",
        "Кот д'Ивуар",
    ],
}

# Кандидаты на алиасы, если понадобится:
#   Тайвань (китай) -> Тайвань (название чувствительное)
#   Виргинские острова, США — находятся и так по началу названия
#   («виргинские»), алиасы не требуются.


def normalize_lookup(value):
    """Строка для поиска в один вид: нижний регистр, ё -> е,
    схлопнутые пробелы. Сводит «Соединённые» и «Соединенные»."""
    return re.sub(r"\s+", " ", value).strip().lower().replace("ё", "е")


def matched_alias_names(query):
    """Названия стран из COUNTRY_SEARCH_ALIASES, чьи алиасы подходят
    под запрос query (запрос уже нормализован через normalize_lookup)."""
    matched = []
    for name, aliases in COUNTRY_SEARCH_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_lookup(alias)
            if (normalized_alias.startswith(query)
                    or query.startswith(normalized_alias + " ")):
                matched.append(name)
                break
    return matched


# Тестовые карточки безвизового режима.
# Пока подключены для Мьянмы, Армении, Саудовской Аравии,
# Таиланда и Китая — чтобы проверить вид на нескольких странах.
COUNTRY_CARDS = {
    "myanmar": {
        "flag": "main/flags/myanmar.svg",
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
        "flag": "main/flags/armenia.svg",
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
    "saudi-arabia": {
        "flag": "main/flags/saudi-arabia.svg",
        "status": "действует",
        "status_key": "active",
        "rule": "Соглашение о взаимной отмене визовых требований",
        "signed": "01.12.2025",
        "from": "11.05.2026",
        "until": "срок не ограничен",
        "stay": "90 дней в календарный год",
        "stay_note": "без права работы",
        "capital": "Эр-Рияд",
        "religion": "Ислам (суннизм)",
        "religion_share": "93%",
        "cities": ["Эр-Рияд", "Джидда", "Мекка", "Медина", "Даммам"],
        "people_note": "оценки · официальная статистика не публикуется",
        "ethnic_groups": [
            {"name": "Арабы", "share": "≈90 %"},
            {"name": "Афро-азиаты", "share": "≈10 %"},
        ],
        "religions": [
            {"name": "Ислам (суннизм)", "share": "93,00 %"},
            {"name": "Христианство", "share": "4,40 %"},
            {"name": "Индуизм", "share": "1,10 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "21.474853",
            "local_name": "Саудовский риял",
            "local_code": "SAR",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 SAR = 21,4749 ₽",
        },
        "note": "Подписано 01.12.2025 в Эр-Рияде. Безвиз не распространяется на хадж и умру в сезон хаджа — для них нужна отдельная виза.",
        "source_label": "МИД РФ · текст соглашения",
        "source_url": "https://www.mid.ru/ru/foreign_policy/international_contracts/international_contracts/2_contract/63093/",
        "unesco_note": "объекты всемирного наследия ЮНЕСКО",
        "unesco": [
            {"name": "Археологический объект Аль-Хиджр", "years": "2008"},
            {"name": "Район ad-Dir’iyah в городе ad-Dir’iyah", "years": "2010"},
            {"name": "Исторический город Джидда - ворота в Мекку", "years": "2014"},
            {"name": "Наскальная живопись в провинции Хаиль", "years": "2015"},
            {"name": "Оазис Аль-Ахса, меняющийся культурный ландшафт", "years": "2018"},
            {"name": "Культурный район Хима", "years": "2021"},
            {"name": "Урук Бани Маарид", "years": "2023"},
            {"name": "Культурный ландшафт археологической зоны Аль-Фау", "years": "2024"},
        ],
    },
    "thailand": {
        "flag": "main/flags/thailand.svg",
        "status": "действует",
        "status_key": "active",
        "rule": "Соглашение об отказе от визовых формальностей",
        "signed": "13.12.2005",
        "from": "24.03.2007",
        "until": "срок не ограничен",
        "stay": "30 дней",
        "stay_note": "с 2026 снова 30, а не 60",
        "capital": "Бангкок",
        "religion": "Буддизм (тхеравада)",
        "religion_share": "93%",
        "cities": ["Бангкок", "Чиангмай", "Пхукет", "Паттайя", "Хатъяй"],
        "people_note": "оценки · перепись не учитывает этничность",
        "ethnic_groups": [
            {"name": "Тайцы", "share": "≈80 %"},
            {"name": "Китайцы", "share": "≈10 %"},
            {"name": "Малайцы", "share": "≈3 %"},
        ],
        "religions": [
            {"name": "Буддизм (тхеравада)", "share": "93,00 %"},
            {"name": "Ислам", "share": "5,00 %"},
            {"name": "Христианство", "share": "1,20 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "2.381508",
            "local_name": "Тайский бат",
            "local_code": "THB",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 THB = 2,3815 ₽",
        },
        "note": "Соглашение от 13.12.2005. В 2024–2026 годах срок был 60 дней, с 2026 года — снова 30.",
        "source_label": "Википедия · визовые требования",
        "source_url": "https://ru.wikipedia.org/wiki/Визовые_требования_для_граждан_России",
        "unesco_note": "объекты всемирного наследия ЮНЕСКО",
        "unesco": [
            {"name": "Исторический город Аютия и соседние исторические города", "years": "1991"},
            {"name": "Исторический город Сукотаи и соседние исторические города", "years": "1991"},
            {"name": "Резерваты дикой природы Тхунгъяй и Хуайкхакхэнг", "years": "1991"},
            {"name": "Археологический памятник Банчианг", "years": "1992"},
            {"name": "Лесной комплекс Донгфаяйен-Кхауяй", "years": "2005"},
            {"name": "Лесной комплекс Каенг Крачан", "years": "2021"},
            {"name": "Древний город Си Тхеп и связанные с ним памятники Дваравати", "years": "2023"},
            {"name": "Исторический парк Пху Пхра Бат", "years": "2024"},
            {"name": "Ват-Пхра-Махатхат-Ворамахавихан, Накхонситхаммарат", "years": "2026"},
        ],
    },
    "china": {
        "flag": "main/flags/china.svg",
        "status": "действует",
        "status_key": "active",
        "rule": "Односторонний пробный безвизовый режим Китая",
        "signed": "—",
        "from": "15.09.2025",
        "until": "31.12.2027",
        "stay": "30 дней за поездку",
        "stay_note": "продлён до 31.12.2027",
        "capital": "Пекин",
        "religion": "Господствующей нет",
        "religion_share": "",
        "cities": ["Шанхай", "Пекин", "Чунцин", "Гуанчжоу", "Шэньчжэнь"],
        "people_note": "перепись 2020 · религиозный состав не публикуется",
        "ethnic_groups": [
            {"name": "Ханьцы", "share": "91,10 %"},
            {"name": "Чжуаны", "share": "1,40 %"},
            {"name": "Уйгуры", "share": "0,80 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "12.031464",
            "local_name": "Китайский юань",
            "local_code": "CNY",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 CNY = 12,0315 ₽",
        },
        "note": "Китай ввёл безвиз для россиян с 15.09.2025 на пробный период; в мае 2026 продлил до 31.12.2027. Россия ответила аналогичным указом с 01.12.2025.",
        "source_label": "ТАСС · продление до 31.12.2027",
        "source_url": "https://tass.ru/politika/27933829",
        "unesco_note": "объекты всемирного наследия ЮНЕСКО · 61",
        "unesco": [
            {"name": "Великая Китайская Стена", "years": "1987"},
            {"name": "Гора Тайшань", "years": "1987"},
            {"name": "Гробница первого императора династии Цинь", "years": "1987"},
            {"name": "Дворцы императоров династий Мин и Цин в Пекине и Шэньяне", "years": "1987, 2004"},
            {"name": "Пещеры Могао", "years": "1987"},
            {"name": "Стоянка «пекинского человека» в Чжоукоудяне", "years": "1987"},
            {"name": "Гора Хуаншань", "years": "1990"},
            {"name": "Пейзажная достопримечательная зона Улинъюань", "years": "1992"},
            {"name": "Пейзажная достопримечательная зона Хуанлун", "years": "1992"},
            {"name": "Пейзажная достопримечательная зона Цзючжайгоу", "years": "1992"},
            {"name": "Горная императорская резиденция и окружающие его храмы в Чэндэ", "years": "1994"},
            {"name": "Исторический ансамбль дворца Потала в городе Лхаса", "years": "1994, 2000, 2001"},
            {"name": "Комплекс древних строений в горах Уданшань", "years": "1994"},
            {"name": "Храм и гробница Конфуция и имение семьи Кун в городе Цюйфу", "years": "1994"},
            {"name": "Гора Эмэйшань и статуя «Большой Будда» в Лэшани", "years": "1996"},
            {"name": "Национальный парк Лушань", "years": "1996"},
            {"name": "Исторический город Пинъяо", "years": "1997"},
            {"name": "Классические сады в городе Сучжоу", "years": "1997, 2000"},
            {"name": "Старый город Лицзян", "years": "1997"},
            {"name": "Летний дворец и императорский парк в Пекине", "years": "1998"},
            {"name": "Храм Неба: императорский жертвенный алтарь в Пекине", "years": "1998"},
            {"name": "Горы Уишань", "years": "1999"},
            {"name": "Наскальные рельефы в Дацзу", "years": "1999"},
            {"name": "Гора Цинчэншань и древняя оросительная система Дуцзянъянь", "years": "2000"},
            {"name": "Гробницы императоров династий Мин и Цин", "years": "2000, 2003, 2004"},
            {"name": "Пещерные храмы Лунмэнь", "years": "2000"},
            {"name": "Старинные деревни Сиди и Хунцунь на юге провинции Аньхой", "years": "2000"},
            {"name": "Пещерные храмы Юньган", "years": "2001"},
            {"name": "Охраняемые территории трёх параллельных рек провинции Юньнань", "years": "2003"},
            {"name": "Столичные города и гробницы древнего царства Когурё", "years": "2004"},
            {"name": "Исторический центр города Макао (Аомынь)", "years": "2005"},
            {"name": "Древний город Иньсюй", "years": "2006"},
            {"name": "Резерваты гигантской панды в провинции Сычуань", "years": "2006"},
            {"name": "South China Karst", "years": "2007, 2014"},
            {"name": "Диаолоу и деревни Кайпинга", "years": "2007"},
            {"name": "Национальный парк горы Саньциншань", "years": "2008"},
            {"name": "Тулоу провинции Фуцзянь", "years": "2008"},
            {"name": "Mount Wutai", "years": "2009"},
            {"name": "Данься, Китай", "years": "2010"},
            {"name": "Исторические памятники Деньфень в «Центре Неба и Земли»", "years": "2010"},
            {"name": "West Lake Cultural Landscape of Hangzhou", "years": "2011"},
            {"name": "Chengjiang Fossil Site", "years": "2012"},
            {"name": "Site of Xanadu", "years": "2012"},
            {"name": "Cultural Landscape of Honghe Hani Rice Terraces", "years": "2013"},
            {"name": "Xinjiang Tianshan", "years": "2013"},
            {"name": "Silk Roads: the Routes Network of Chang'an-Tianshan Corridor", "years": "2014"},
            {"name": "The Grand Canal", "years": "2014"},
            {"name": "Архитектурный комплекс китайских правителей «тусы»", "years": "2015"},
            {"name": "Zuojiang Huashan Rock Art Cultural Landscape", "years": "2016"},
            {"name": "Шэньнунцзя в провинции Хубэй", "years": "2016"},
            {"name": "Kulangsu, a Historic International Settlement", "years": "2017"},
            {"name": "Qinghai Hoh Xil", "years": "2017"},
            {"name": "Фаньцзиншань", "years": "2018"},
            {"name": "Ареалы обитания перелетных птиц вдоль побережья Желтого моря и Бохайского залива", "years": "2019, 2024"},
            {"name": "Руины древнего города Лянчжу", "years": "2019"},
            {"name": "Цюаньчжоу: мировой центр торговли в Китае эпохи династий Сун-Юань", "years": "2021"},
            {"name": "Культурный ландшафт древних чайных лесов горы Цзинмай в Пуэре", "years": "2023"},
            {"name": "Пустыня Бадын-Джаран — песчаные дюны и озера", "years": "2024"},
            {"name": "Центральная ось Пекина: архитектурный ансамбль, представляющий идеальный порядок китайской столицы", "years": "2024"},
            {"name": "Императорские гробницы Си Ся", "years": "2025"},
            {"name": "Объекты ремесленного фарфорового производства Цзиндэчжэня", "years": "2026"},
        ],
    },
    "australia": {
        "flag": "main/flags/australia.svg",
        "status": "—",
        "status_key": "unknown",
        "rule": "—",
        "signed": "—",
        "from": "—",
        "until": "—",
        "stay": "—",
        "stay_note": "визовые данные пока не внесены",
        "capital": "Канберра",
        "religion": "Христианство",
        "religion_share": "44%",
        "cities": ["Сидней", "Мельбурн", "Брисбен", "Перт", "Аделаида"],
        "people_note": "перепись 2021 · официальная классификация",
        "ethnic_groups": [
            {"name": "Англо-австралийцы", "share": "57,70 %"},
            {"name": "Китайцы", "share": "5,50 %"},
            {"name": "Индийцы", "share": "2,90 %"},
        ],
        "religions": [
            {"name": "Христианство", "share": "43,90 %"},
            {"name": "Ислам", "share": "3,20 %"},
            {"name": "Индуизм", "share": "1,90 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "52.344955",
            "local_name": "Австралийский доллар",
            "local_code": "AUD",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 AUD = 52,3450 ₽",
        },
        "note": "Карточка подключена в тестовом режиме: визовые данные и источники будут добавлены позже.",
        "source_label": "—",
        "source_url": "",
        "unesco_note": "объекты всемирного наследия ЮНЕСКО",
        "unesco": [
            {"name": "Большой Барьерный риф", "years": "1981"},
            {"name": "Остров Кенгуру (Фрейзер)", "years": "1992"},
            {"name": "Гора Улуру — Ката-Тьюта", "years": "1987, 1994"},
            {"name": "Сиднейский оперный театр", "years": "2007"},
            {"name": "Природоохранные зоны Тасмании", "years": "1982"},
        ],
    },
    "lithuania": {
        "flag": "main/flags/lithuania.svg",
        "status": "—",
        "status_key": "unknown",
        "rule": "—",
        "signed": "—",
        "from": "—",
        "until": "—",
        "stay": "—",
        "stay_note": "визовые данные пока не внесены",
        "capital": "Вильнюс",
        "religion": "Христианство (католицизм)",
        "religion_share": "74%",
        "cities": ["Вильнюс", "Каунас", "Клайпеда", "Шяуляй", "Паневежис"],
        "people_note": "перепись 2021",
        "ethnic_groups": [
            {"name": "Литовцы", "share": "84,60 %"},
            {"name": "Поляки", "share": "6,50 %"},
            {"name": "Русские", "share": "5,00 %"},
        ],
        "religions": [
            {"name": "Католицизм", "share": "74,20 %"},
            {"name": "Православие", "share": "3,70 %"},
            {"name": "Нет религии", "share": "6,10 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "93.4157",
            "local_name": "Евро",
            "local_code": "EUR",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 EUR = 93,4157 ₽",
        },
        "note": "Карточка подключена в тестовом режиме: визовые данные и источники будут добавлены позже.",
        "source_label": "—",
        "source_url": "",
    },
    "turkey": {
        "flag": "main/flags/turkey.svg",
        "status": "—",
        "status_key": "unknown",
        "rule": "—",
        "signed": "—",
        "from": "—",
        "until": "—",
        "stay": "—",
        "stay_note": "визовые данные пока не внесены",
        "capital": "Анкара",
        "religion": "Ислам (суннизм)",
        "religion_share": "99%",
        "cities": ["Стамбул", "Анкара", "Измир", "Бурса", "Анталья"],
        "people_note": "оценки · адресная перепись",
        "ethnic_groups": [
            {"name": "Турки", "share": "≈75 %"},
            {"name": "Курды", "share": "≈19 %"},
            {"name": "Арабы", "share": "≈2 %"},
        ],
        "religions": [
            {"name": "Ислам (суннизм)", "share": "99,00 %"},
            {"name": "Христианство", "share": "0,20 %"},
        ],
        "rates": {
            "date": "28.10.2026",
            "rub_per_usd": "80.5307",
            "rub_per_local": "1.912851",
            "local_name": "Турецкая лира",
            "local_code": "TRY",
            "usd_line": "1 USD = 80,5307 ₽",
            "local_line": "1 TRY = 1,9129 ₽",
        },
        "note": "Карточка подключена в тестовом режиме: визовые данные и источники будут добавлены позже.",
        "source_label": "—",
        "source_url": "",
        "unesco_note": "объекты всемирного наследия ЮНЕСКО",
        "unesco": [
            {"name": "Исторические зоны Стамбула", "years": "1985"},
            {"name": "Каппадокия и наскальные памятники Гёреме", "years": "1985"},
            {"name": "Хиераполис — Памуккале", "years": "1988"},
            {"name": "Немрут-Даг", "years": "1987"},
            {"name": "Античный город Эфес", "years": "2015"},
        ],
    },
}


# Автосгенерированные карточки всех стран (scripts/build_cards.py):
# флаг + данные из country-cards. Ручные карточки выше имеют приоритет.
try:
    _cards_auto_path = Path(__file__).resolve().parent.parent / "main" / "data" / "cards_auto.json"
    _cards_auto = json.loads(_cards_auto_path.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _cards_auto = {}

COUNTRY_CARDS = {**_cards_auto, **COUNTRY_CARDS}


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
            # Ищем по префиксу, как и раньше: «Аб» -> Абхазия,
            # «бха» ничего не найдёт. Нормализуем ё->е, чтобы
            # «Соединённые» находило «Соединенные». Спецсимволы LIKE
            # экранируем, чтобы % и _ в запросе не превращались в шаблон.
            normalized = normalize_lookup(search)
            escaped = (
                normalized
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            search_conditions = ["REPLACE(LOWER(oksm.name), 'ё', 'е') LIKE %s"]
            search_params = [f"{escaped}%"]

            # Тот же поиск по алиасам: «Америка», «США» и т.п.
            alias_names = matched_alias_names(normalized)
            if alias_names:
                placeholders = ", ".join(["%s"] * len(alias_names))
                search_conditions.append(f"oksm.name IN ({placeholders})")
                search_params.extend(alias_names)

            conditions.append("(" + " OR ".join(search_conditions) + ")")
            params.extend(search_params)

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
    # Псевдонимы URL-слагов: пользовательский слаг -> слаг в БД.
    # Например, ISO-название "Turkiye" даёт slug "turkiye",
    # а в URL используем привычное "turkey".
    slug_aliases = {"turkey": "turkiye"}
    slug_alias_reverse = {v: k for k, v in slug_aliases.items()}
    slugs = [slug]
    if slug in slug_aliases:
        slugs.append(slug_aliases[slug])

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
            WHERE oksm.slug = ANY(%s)
        """, [slugs])

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

    db_slug = country.get("slug") or ""
    card_slug = slug if slug in COUNTRY_CARDS else (
        db_slug if db_slug in COUNTRY_CARDS else slug_alias_reverse.get(db_slug, "")
    )

    return render(request, "country_detail.html", {
        "country": country,
        "card": COUNTRY_CARDS.get(card_slug),
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
