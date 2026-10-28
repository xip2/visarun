/* ===== КАЛЬКУЛЯТОР: РУБЛЬ — МЕСТНАЯ ВАЛЮТА — ДОЛЛАР ===== */

(function () {
    "use strict";

    var root = document.querySelector(".visa-rates");
    if (!root) {
        return;
    }

    var rubPerUsd = parseFloat(root.dataset.rubPerUsd);
    var rubPerLocal = parseFloat(root.dataset.rubPerLocal);

    if (!rubPerUsd || !rubPerLocal) {
        return;
    }

    var fields = {
        rub: document.getElementById("rate-rub"),
        local: document.getElementById("rate-local"),
        usd: document.getElementById("rate-usd")
    };

    // Сколько рублей стоит одна единица валюты.
    var rubValue = {
        rub: 1,
        local: rubPerLocal,
        usd: rubPerUsd
    };

    var formatter = new Intl.NumberFormat("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    function parseValue(text) {
        var clean = String(text).replace(/\s/g, "").replace(",", ".");
        var number = parseFloat(clean);
        return isFinite(number) ? number : null;
    }

    function formatValue(number) {
        return formatter.format(number);
    }

    function update(source) {
        var amount = parseValue(fields[source].value);

        if (amount === null) {
            Object.keys(fields).forEach(function (key) {
                if (key !== source) {
                    fields[key].value = "";
                }
            });
            return;
        }

        var inRub = amount * rubValue[source];

        Object.keys(fields).forEach(function (key) {
            if (key === source) {
                return;
            }
            fields[key].value = formatValue(inRub / rubValue[key]);
        });
    }

    Object.keys(fields).forEach(function (key) {
        var field = fields[key];
        if (!field) {
            return;
        }

        field.addEventListener("input", function () {
            update(key);
        });

        field.addEventListener("focus", function () {
            field.select();
        });

        field.addEventListener("blur", function () {
            var amount = parseValue(field.value);
            if (amount !== null) {
                field.value = formatValue(amount);
            }
        });
    });

    // Стартовый расчёт: 1 000 рублей.
    update("rub");
})();
