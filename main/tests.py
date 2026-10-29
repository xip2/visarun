from django.test import SimpleTestCase

from main.views import matched_alias_names, normalize_lookup


class CountrySearchAliasTests(SimpleTestCase):
    """Поиск по алиасам в поле «Поиск страны»."""

    def find(self, query):
        return matched_alias_names(normalize_lookup(query))

    def test_usa(self):
        self.assertEqual(self.find("Соединенные Штаты"), ["Соединенные Штаты"])
        self.assertEqual(self.find("Соединенные Штаты Америки"), ["Соединенные Штаты"])
        self.assertEqual(self.find("USA"), ["Соединенные Штаты"])
        self.assertEqual(self.find("us"), ["Соединенные Штаты"])

    def test_yo_is_normalized(self):
        # В базе «Соединенные» через «е», пользователь печатает «ё».
        self.assertEqual(self.find("Соединённые Штаты"), ["Соединенные Штаты"])

    def test_short_spellings(self):
        self.assertEqual(self.find("США"), ["Соединенные Штаты"])
        self.assertEqual(self.find("сша"), ["Соединенные Штаты"])

    def test_prefix_of_alias(self):
        # Человек не допечатал слово — страна всё равно находится.
        self.assertEqual(self.find("Амер"), ["Соединенные Штаты"])
        self.assertEqual(self.find("Соед"), ["Соединенные Штаты"])
        self.assertEqual(self.find("СШ"), ["Соединенные Штаты"])

    def test_uk(self):
        self.assertEqual(self.find("Великобритания"), ["Соединенное Королевство"])
        self.assertEqual(self.find("Англия"), ["Соединенное Королевство"])
        self.assertEqual(self.find("Британ"), ["Соединенное Королевство"])
        self.assertEqual(self.find("UK"), ["Соединенное Королевство"])

    def test_uae(self):
        self.assertEqual(self.find("ОАЭ"), ["Объединенные Арабские Эмираты"])
        self.assertEqual(self.find("Эмират"), ["Объединенные Арабские Эмираты"])
        self.assertEqual(self.find("Дубай"), ["Объединенные Арабские Эмираты"])

    def test_koreas_are_not_confused(self):
        self.assertEqual(self.find("Южная Корея"), ["Корея, Республика"])
        self.assertEqual(self.find("КНДР"),
                         ["Корея, Народно-Демократическая Республика"])
        # «Корея» без уточнения ведёт к Республики Корея,
        # КНДР при этом находится по началу своего названия.
        self.assertEqual(self.find("Корея"), ["Корея, Республика"])

    def test_long_official_names(self):
        self.assertEqual(self.find("Сирия"), ["Сирийская Арабская Республика"])
        self.assertEqual(self.find("Лаос"),
                         ["Лаосская Народно-Демократическая Республика"])
        self.assertEqual(self.find("Северная Македония"), ["Республика Македония1"])
        self.assertEqual(self.find("Македон"), ["Республика Македония1"])
        self.assertEqual(self.find("Кыргызстан"), ["Киргизия"])
        self.assertEqual(self.find("Голландия"), ["Нидерланды"])

    def test_cape_verde_and_ivory_coast(self):
        self.assertEqual(self.find("Зеленый Мыс"), ["Кабо-Верде"])
        self.assertEqual(self.find("Зеленого Мыса"), ["Кабо-Верде"])
        # В базе обратный апостроф («д`Ивуар»), человек печатает нормальный.
        self.assertEqual(self.find("Кот-д'Ивуар"), ["Кот д`Ивуар"])
        self.assertEqual(self.find("Берег Слоновой Кости"), ["Кот д`Ивуар"])

    def test_no_match(self):
        self.assertEqual(self.find("бха"), [])
        self.assertEqual(self.find("моя страна"), [])
        self.assertEqual(self.find("Россия"), [])

    def test_normalize_lookup(self):
        self.assertEqual(normalize_lookup("  Соединённые   Штаты "), "соединенные штаты")
        self.assertEqual(normalize_lookup("USA"), "usa")
