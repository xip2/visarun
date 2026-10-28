-- ============================================================
--  Visarun: заливка данных из main/data/*.csv
-- ============================================================
--  Запускать ПОСЛЕ db/tables.sql, из корня проекта:
--    psql -U jacob -d vr_project -f db/import.sql
--
--  \copy (с обратной косой чертой) читает файлы на машине,
--  где запущен psql, а не на сервере PostgreSQL — поэтому
--  пути относительные и работают локально.
-- ============================================================

\set ON_ERROR_STOP on
\encoding UTF8
SET client_encoding = 'UTF8';

BEGIN;

-- ------------------------------------------------------------
-- 1. oksm — 252 страны, русские названия
--    В countries.csv названия могут содержать запятую
--    ("Боливия, многонациональное государство"), поэтому
--    файл читаем как текст и режем по ПЕРВОЙ запятой.
-- ------------------------------------------------------------
CREATE TEMP TABLE _oksm_raw (line text);

\copy _oksm_raw (line) FROM 'main/data/countries.csv' WITH (FORMAT text)

INSERT INTO oksm (code, name, slug)
SELECT code, name, 'tmp-' || code
FROM (
    SELECT split_part(l, ',', 1)::int AS code,
           trim(both '"' from substr(l, strpos(l, ',') + 1)) AS name
    FROM (SELECT rtrim(line, E'\r') AS l FROM _oksm_raw) t
) s;

-- ------------------------------------------------------------
-- 2. groups — объединения стран
-- ------------------------------------------------------------
\copy groups (code, eu_name, name) FROM 'main/data/groups.csv' WITH (FORMAT csv)

-- ------------------------------------------------------------
-- 3. oksm_groups — страна -> объединение
-- ------------------------------------------------------------
\copy oksm_groups (id, country_id, group_id) FROM 'main/data/country_groups.csv' WITH (FORMAT csv)

SELECT setval(
    pg_get_serial_sequence('oksm_groups', 'id'),
    (SELECT max(id) FROM oksm_groups)
);

-- ------------------------------------------------------------
-- 4. country_iso — справочник ISO 3166-1
--    Читаем всё как текст (в файле есть "" и пустые поля),
--    потом приводим типы и пустые строки превращаем в NULL.
-- ------------------------------------------------------------
CREATE TEMP TABLE _iso_raw (
    name                     text,
    alpha_2                  text,
    alpha_3                  text,
    country_code             text,
    iso_3166_2               text,
    region                   text,
    sub_region               text,
    intermediate_region      text,
    region_code              text,
    sub_region_code          text,
    intermediate_region_code text
);

\copy _iso_raw FROM 'main/data/country_iso.csv' WITH (FORMAT csv)

INSERT INTO country_iso (
    name, alpha_2, alpha_3, country_code, iso_3166_2,
    region, sub_region, intermediate_region,
    region_code, sub_region_code, intermediate_region_code
)
SELECT
    name,
    alpha_2,
    alpha_3,
    country_code::int,
    iso_3166_2,
    NULLIF(region, ''),
    NULLIF(sub_region, ''),
    NULLIF(intermediate_region, ''),
    NULLIF(region_code, '')::int,
    NULLIF(sub_region_code, '')::int,
    NULLIF(intermediate_region_code, '')::int
FROM _iso_raw;

-- ------------------------------------------------------------
-- 5. visa_rule — визовые правила
--    В CSV бывает 3, 4 или 6 колонок, поэтому COPY в CSV-режиме
--    не подходит (он требует одинаковое число полей). Читаем
--    файл построчно и режем по запятой. Запятых внутри полей
--    в этом файле нет (проверено), так что разбор безопасен.
--    Поля: 1=страна 2=статус 3=дни 4=статус2 5=дни2 6=дни3.
-- ------------------------------------------------------------
CREATE TEMP TABLE _vr_raw (line text);

\copy _vr_raw (line) FROM 'main/data/visa_rule.csv' WITH (FORMAT text)

INSERT INTO visa_rule (name, visa_status, days)
SELECT
    trim(p[1]),
    regexp_replace(trim(p[2]), '\s+\d+$', ''),
    COALESCE(
        NULLIF(regexp_replace(p[3], '\D', '', 'g'), '')::int,
        NULLIF(regexp_replace(p[4], '\D', '', 'g'), '')::int,
        NULLIF(regexp_replace(p[5], '\D', '', 'g'), '')::int,
        NULLIF(regexp_replace(p[6], '\D', '', 'g'), '')::int,
        NULLIF(substring(trim(p[2]) from '(\d+)$'), '')::int
    )
FROM (
    SELECT regexp_split_to_array(rtrim(line, E'\r'), ',') AS p
    FROM _vr_raw
) t;

-- ------------------------------------------------------------
-- 6. Связываем country_iso с oksm.
--    В countries.csv id идут ровно в порядке возрастания
--    ISO-кодов (проверено: Россия=185 -> 643, США=240 -> 840
--    и т.д.), поэтому нумеруем country_iso по country_code
--    и получаем oksm_code = 1..249.
-- ------------------------------------------------------------
WITH ordered AS (
    SELECT country_code,
           row_number() OVER (ORDER BY country_code) AS n
    FROM country_iso
)
UPDATE country_iso ci
SET oksm_code = o.n
FROM ordered o
WHERE ci.country_code = o.country_code;

-- ------------------------------------------------------------
-- 7. Связываем visa_rule с oksm через country_iso.
--    Часть названий в visa_rule.csv не совпадает с ISO —
--    для них таблица синонимов.
-- ------------------------------------------------------------
CREATE TEMP TABLE _alias (old_name text PRIMARY KEY, iso_name text NOT NULL);

INSERT INTO _alias (old_name, iso_name) VALUES
    ('Cape Verde',                  'Cabo Verde'),
    ('Congo (Dem. Rep.)',           'Congo, Democratic Republic of the'),
    ('Venezuela',                   'Venezuela, Bolivarian Republic of'),
    ('United Kingdom',              'United Kingdom of Great Britain and Northern Ireland'),
    ('Taiwan',                      'Taiwan, Province of China'),
    ('Cote d''Ivoire (Ivory Coast)', 'Côte d''Ivoire'),
    ('Tanzania',                    'Tanzania, United Republic of'),
    ('Moldova',                     'Moldova, Republic of'),
    ('St. Vincent and the Grenadines', 'Saint Vincent and the Grenadines'),
    ('Iran',                        'Iran, Islamic Republic of'),
    ('Czech Republic',              'Czechia'),
    ('Brunei',                      'Brunei Darussalam'),
    ('Vatican City',                'Holy See'),
    ('Bolivia',                     'Bolivia, Plurinational State of'),
    ('South Korea',                 'Korea, Republic of'),
    ('Micronesia',                  'Micronesia, Federated States of'),
    ('North Korea',                 'Korea, Democratic People''s Republic of'),
    ('Laos',                        'Lao People''s Democratic Republic'),
    ('Palestinian Territories',     'Palestine, State of'),
    ('Netherlands',                 'Netherlands, Kingdom of the'),
    ('Syria',                       'Syrian Arab Republic');

UPDATE visa_rule v
SET oksm_code = ci.oksm_code
FROM country_iso ci
WHERE ci.name = COALESCE(
    (SELECT a.iso_name FROM _alias a WHERE a.old_name = v.name),
    v.name
);

-- ------------------------------------------------------------
-- 8. Человекочитаемые slug для URL: /country/germany/
--    Берём английское ISO-название, убираем апострофы и точки,
--    снимаем акценты (unaccent), всё не-латинское -> дефис.
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS unaccent;

UPDATE oksm o
SET slug = trim(both '-' from regexp_replace(
        regexp_replace(
            unaccent(lower(replace(replace(ci.name, '''', ''), '.', ''))),
            '[^a-z0-9]+', '-', 'g'
        ),
        '-+', '-', 'g'))
FROM country_iso ci
WHERE ci.oksm_code = o.code;

-- Три страны есть только в countries.csv (нет ISO-названия) —
-- slug придуманы вручную.
UPDATE oksm SET slug = 'abkhazia'        WHERE name = 'Абхазия';
UPDATE oksm SET slug = 'south-ossetia'   WHERE name = 'Южная Осетия';
UPDATE oksm SET slug = 'channel-islands' WHERE name = 'Нормандские острова';

COMMIT;

-- ------------------------------------------------------------
-- Проверка: что загрузилось
-- ------------------------------------------------------------
\echo '--- строки в таблицах ---'
SELECT 'oksm'         AS table_name, count(*) FROM oksm
UNION ALL
SELECT 'groups',                     count(*) FROM groups
UNION ALL
SELECT 'oksm_groups',                count(*) FROM oksm_groups
UNION ALL
SELECT 'country_iso',                count(*) FROM country_iso
UNION ALL
SELECT 'visa_rule',                  count(*) FROM visa_rule;

\echo '--- без привязки к oksm (ожидаем только Kosovo) ---'
SELECT v.name, v.visa_status
FROM visa_rule v
WHERE v.oksm_code IS NULL;

\echo '--- страны без slug (должно быть 0 строк) ---'
SELECT code, name FROM oksm WHERE slug LIKE 'tmp-%';

\echo '--- примеры slug ---'
SELECT code, name, slug FROM oksm ORDER BY code LIMIT 8;

\echo '--- пример: первые 10 стран ---'
SELECT o.name, COALESCE(v.visa_status, '-') AS status, v.days
FROM oksm o
LEFT JOIN visa_rule v ON v.oksm_code = o.code
ORDER BY o.code
LIMIT 10;
