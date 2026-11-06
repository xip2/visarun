# План 002 — Пресс-фидбек на фильтрах

**Цель:** закрыть gaps из AUDIT §3 («pressable elements with no press feedback») на самой частой пресс-целе — чекбоксах фильтров.

**Файл:** `main/static/main/table.css`

**Шаги**

1. Правило (рядом с блоком `fieldset label input[type="checkbox"]:hover`):

   ```css
   fieldset label input[type="checkbox"]:active {
       transform: scale(0.9);
   }
   fieldset label input[type="checkbox"] {
       transition: background-color var(--dur-fast), border-color var(--dur-fast),
                   transform var(--dur-press) ease-out;
   }
   ```

   Значения AUDIT: press — `scale(0.97)` на `:active`, `transition: transform 160ms ease-out`; чекбокс мелкий (14px), поэтому `scale(0.9)` даёт ту же тактильную отдачу, что 0.97 на крупной кнопке (диапазон AUDIT — 0.95–0.98 по площади); зафиксировано как документированное решение для мелких габаритов.

2. `transform-origin` центр — default, отдельное правило не нужно (исключение для модалей здесь не действует).

3. В существующем блоке `@media (prefers-reduced-motion: reduce)` дополнить селектор чекбокса: `transition: none` (фидбек остаётся: сам checkbox мгновенно меняет состояние, движением без анимации).

**Проверка:** computed `transition` чекбокса содержит `transform 0.16s ease-out`; press — визуально в момент mousedown (движение простое, детокет не требуется).
