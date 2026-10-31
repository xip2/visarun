-- ============================================================
--  Visarun: заливка данных из main/data/*.csv
-- ============================================================
--  Запускать ПОСЛЕ db/tables.sql, из корня проекта:
--  psql -U jacob -d vr_project -f db/import.sql
--
--  Порядок:
--    1. countries      — merge iso_country.csv +
--                        countries_russian_format_oksm.csv
--    2. groups         — как есть
--    3. country_group  — country_groups.csv с пересчётом
--                        легаси-кодов 1..252 в country_id
--    4. visa_rule      — visa_rule_with_id.csv (id уже проставлен)
-- ============================================================

\set ON_ERROR_STOP on
\encoding UTF8
SET client_encoding = 'UTF8';

BEGIN;

-- идемпотентность: чистим целевые таблицы перед заливкой
TRUNCATE visa_rule, country_group, groups, countries RESTART IDENTITY CASCADE;

-- ------------------------------------------------------------
-- 1. countries — merge двух CSV через FULL JOIN
-- ------------------------------------------------------------
CREATE TEMP TABLE _isoc (
    name_en                  text,
    alpha_2                  text,
    alpha_3                  text,
    code                     text,
    iso_3166_2               text,
    region                   text,
    sub_region               text,
    intermediate_region      text,
    region_code              text,
    sub_region_code          text,
    intermediate_region_code text
);

CREATE TEMP TABLE _ru (
    code             text,
    name_ru          text,
    name_ru_full     text
);

\copy _isoc FROM 'main/data/iso_country.csv' WITH (FORMAT csv)
\copy _ru   FROM 'main/data/countries_russian_format_oksm.csv' WITH (FORMAT csv)

INSERT INTO countries (
    country_id, alpha_2, alpha_3, name_en,
    name_ru, name_ru_full,
    iso_3166_2, region, region_code,
    sub_region, sub_region_code,
    intermediate_region, intermediate_region_code
)
SELECT
    COALESCE(
        CASE WHEN i.code ~ '^\d+$' THEN i.code::int END,
        CASE WHEN r.code ~ '^\d+$' THEN r.code::int END),
    NULLIF(i.alpha_2, ''),
    NULLIF(i.alpha_3, ''),
    NULLIF(i.name_en, ''),
    NULLIF(r.name_ru, ''),
    NULLIF(r.name_ru_full, ''),
    NULLIF(i.iso_3166_2, ''),
    NULLIF(i.region, ''),
    NULLIF(i.region_code, '')::int,
    NULLIF(i.sub_region, ''),
    NULLIF(i.sub_region_code, '')::int,
    NULLIF(i.intermediate_region, ''),
    NULLIF(i.intermediate_region_code, '')::int
FROM _isoc i
FULL JOIN _ru r
  ON (CASE WHEN i.code ~ '^\d+$' THEN i.code::int END)
   = (CASE WHEN r.code ~ '^\d+$' THEN r.code::int END);

-- ------------------------------------------------------------
-- 2. groups — объединения стран
-- ------------------------------------------------------------
\copy groups (group_id, eu_name, name) FROM 'main/data/groups.csv' WITH (FORMAT csv)

-- ------------------------------------------------------------
-- 3. country_group — страна -> объединение.
--    В country_groups.csv легаси-коды 1..252. Пересчёт:
--    1..249 = row_number() по возрастанию country_id среди
--    ISO-строк (проверено: легаси 185 -> 643, 240 -> 840);
--    250 -> 895 (Абхазия), 251 -> 896 (Южная Осетия);
--    252 (Нормандские острова) в новой справочнике нет —
--    строка удаляется.
-- ------------------------------------------------------------
CREATE TEMP TABLE _lg (id text, country_id text, group_id text);
\copy _lg FROM 'main/data/country_groups.csv' WITH (FORMAT csv)

WITH legacy2new AS (
    SELECT g.n AS old, c.country_id AS new
    FROM (SELECT generate_series(1, 249) AS n) g
    JOIN (
        SELECT country_id, row_number() OVER (ORDER BY country_id) AS rn
        FROM countries
        WHERE alpha_2 IS NOT NULL
    ) c ON c.rn = g.n
    UNION ALL
    SELECT 250, 895
    UNION ALL
    SELECT 251, 896
)
INSERT INTO country_group (country_id, group_id)
SELECT m.new, l.group_id::int
FROM _lg l
JOIN legacy2new m ON m.old = l.country_id::int;

SELECT setval(
    pg_get_serial_sequence('country_group', 'id'),
    (SELECT max(id) FROM country_group)
);

-- ------------------------------------------------------------
-- 4. visa_rule — visa_rule_with_id.csv, первая колонка = id
--    (понадобится NULL для Косово). Формат остатка прежний:
--    2=имя 3=статус 4=дни 5=статус2 6=дни2 ...
-- ------------------------------------------------------------
CREATE TEMP TABLE _vr_raw (line text);
\copy _vr_raw (line) FROM 'main/data/visa_rule_with_id.csv' WITH (FORMAT text)

INSERT INTO visa_rule (name, visa_status, days, country_id)
SELECT
    trim(p[2]),
    regexp_replace(trim(p[3]), '\s+\d+$', ''),
    COALESCE(
        NULLIF(regexp_replace(p[4], '\D', '', 'g'), '')::int,
        NULLIF(regexp_replace(p[6], '\D', '', 'g'), '')::int,
        NULLIF(regexp_replace(p[8], '\D', '', 'g'), '')::int,
        NULLIF(substring(trim(p[3]) from '(\d+)$'), '')::int
    ),
    NULLIF(trim(p[1]), '')::int
FROM (
    SELECT regexp_split_to_array(rtrim(line, E'\r'), ',') AS p
    FROM _vr_raw
) t;

-- ------------------------------------------------------------
-- 5. slug — из английского имени ISO; для не-ISO стран — вручную
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS unaccent;

UPDATE countries
SET slug = trim(both '-' from regexp_replace(
        regexp_replace(
            unaccent(lower(replace(replace(COALESCE(name_en, name_ru), '''', ''), '.', ''))),
            '[^a-z0-9]+', '-', 'g'
        ),
        '-+', '-', 'g'))
WHERE slug IS NULL
  AND NULLIF(name_en, '') IS NOT NULL;

UPDATE countries SET slug = 'abkhazia'      WHERE country_id = 895;
UPDATE countries SET slug = 'south-ossetia' WHERE country_id = 896;
UPDATE countries SET slug = 'dnr'           WHERE country_id = 897;
UPDATE countries SET slug = 'lnr'           WHERE country_id = 898;

COMMIT;
\echo '--- строки в таблицах ---'
SELECT 'countries'     AS table_name, count(*) FROM countries
UNION ALL
SELECT 'groups',                      count(*) FROM groups
UNION ALL
SELECT 'country_group',               count(*) FROM country_group
UNION ALL
SELECT 'visa_rule',                   count(*) FROM visa_rule;

\echo '--- visa_rule без привязки к стране (ожидаем только Kosovo) ---'
SELECT v.name, v.visa_status
FROM visa_rule v
WHERE v.country_id IS NULL;

\echo '--- страны без name_en (только русские: 895-898) ---'
SELECT country_id, name_ru FROM countries WHERE name_en IS NULL;

\echo '--- пример ---'
SELECT c.country_id, c.name_en, c.name_ru, v.visa_status, v.days
FROM countries c
LEFT JOIN visa_rule v ON v.country_id = c.country_id
ORDER BY c.country_id
LIMIT 8;
