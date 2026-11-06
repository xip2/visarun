# План 001 — Токены движения (консолидация)

**Цель:** убрать рукопашные длительности/кривые, ввести общие токены в обоих файлах.

**Файлы**
- `main/static/main/country-card.css`
- `main/static/main/table.css`

**Шаги**
1. В начало каждого файла после комментария-шапки добавить:
   ```css
   :root {
       --dur-fast: 0.15s;   /* hover/цвет, граница, фон */
       --dur-draw: 0.18s;   /* «рисующееся» подчёркивание ссылок */
       --dur-press: 0.16s;  /* пресс-фидбек (план 002) */
   }
   ```
   Кривые: hover/цвет = `ease` (AUDIT §2: hover/color change → ease) — остаётся в правилах как `ease`.
2. Замены (значения по AUDIT, не аппроксимация):
   - `0.15s ease` → `var(--dur-fast) ease`
   - `0.18s ease` → `var(--dur-draw) ease`
   - `0.15s, background-color 0.15s` → `var(--dur-fast)`
   - `transition: color 0.2s ease` (table.css .nav a) → `var(--dur-fast) ease`
3. Не трогать: media-reduce гварды (в них `transition: none`).

**Проверка:** `getComputedStyle` любого из этих элементов показывает `transition-duration` 0.15s/0.18s; детектор design по обоим файлам пуст.
