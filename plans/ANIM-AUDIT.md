# Аудит движения — improve-animations (skill: emilkowalski)

Коммит-штамп аудита: `43654b3` · режим: standard (малый репо, без сабагентов) · движение: чистый CSS, без библиотек и keyframes.

## Отклоненные по reconnaissance (не находки)

- `transition: all` — не найдено (5. Performance чисто).
- `ease-in` на UI — не найдено.
- Анимации на клавиатурных действиях — нет.
- keyframes/entrances/scale(0) — нет.

## Ветted findings (по leverage)

| # | Severity | Категория (AUDIT.md) | Локация | Находка | Фикс |
|---|---|---|---|---|---|
| 1 | MEDIUM | 7. Cohesion & tokens | country-card.css:335,446; table.css:78,161,212,289,328,472 | Длительности и кривые набраны руками: 0.15s/0.18s/0.2s, кривая `ease` — однородные почти-значения без токенов | Токены `--dur-fast/--dur-press/--dur-draw/--ease-ui` в обоих файлах (repo-конвенция: каждый файл самодостаточен), значения по AUDIT.md — не аппроксимация |
| 2 | MEDIUM | 3. Physicality & origin | table.css:215 (fieldset фильтры), 508 (sort-link) | Прессуемые контролы без press-feedback (AUDIT: «pressable elements with no press feedback») | `scale(0.97)` на `:active` + `transform 160ms ease-out`, origin центр; только у чекбокса фильтра (самый частый пресс) |
| 3 | LOW | 2. Easing & duration | table.css:78 (nav) | Ховер-цвет навигации 0.2s — чужой в семействе fast-переходов | Переводим на `--dur-fast` (0.15s), кривая `ease` по решению AUDIT (hover/color → ease) |

## Missed opportunities (не применяются в этом прогоне, задокументированы)

- HTMX-подмена строки таблицы при переключении фильтров — «телепорт» строк. Кандидат: 120ms fade на `tr` при вставке; риск: срабатывание на каждую загрузку страницы. Решение отложено до отдельного запроса.
- Карта стран (map.css): fill/stroke уже переходят — ок.

## Ход исполнения

Планы 001-003 применены в сессии (по явной просьбе пользователя «прогнать приложенько»); верификация: computed-styles в браузере, детектор design (impeccable) по затронутым файлам, редьюсед-моти гварды сохранены.
