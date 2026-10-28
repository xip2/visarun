// Интерактивная SVG-карта мира.
//
// Геометрия стран лежит отдельным файлом main/static/main/world.svg
// (пакет @svg-maps/world, CC BY 4.0). У каждой страны в SVG есть id —
// это ISO 3166-1 alpha-2. По нему скрипт находит данные в JSON,
// который страница отдаёт через json_script, и раскрашивает страну.
//
// Всё остальное — hover-подсказка и переход в карточку страны по клику.

(function () {
    "use strict";

    var container = document.getElementById("world-map");
    var tooltip = document.getElementById("map-tooltip");
    var dataNode = document.getElementById("map-data");

    if (!container || !tooltip || !dataNode) {
        return;
    }

    var countries = {};
    try {
        countries = JSON.parse(dataNode.textContent);
    } catch (e) {
        countries = {};
    }

    var STATUS_LABELS = {
        "visa-free": "Без визы",
        "visa required": "Нужна виза",
        "eVisa": "Электронная виза",
        "visa on arrival": "Виза по прибытии",
        "eTA": "Электронное разрешение на въезд",
        "Arrival Card": "Карточка прибытия",
        "pre-enrollment": "Предварительная регистрация",
        "E-Ticket": "Электронный билет",
        "eVisitors": "Электронная регистрация посетителя",
        "tourist registration": "Туристическая регистрация",
        "tourist card": "Туристическая карта"
    };

    var activePath = null;

    /* ================= текст ================= */

    function pluralDays(n) {
        var value = Math.abs(n) % 100;
        if (value >= 11 && value <= 14) {
            return "дней";
        }
        value %= 10;
        if (value === 1) {
            return "день";
        }
        if (value >= 2 && value <= 4) {
            return "дня";
        }
        return "дней";
    }

    function slugify(value) {
        return String(value)
            .toLowerCase()
            .replace(/[^a-z0-9а-яё]+/gi, "-")
            .replace(/^-+|-+$/g, "");
    }

    /* ================= подсказка ================= */

    function el(className, text) {
        var node = document.createElement("div");
        node.className = className;
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    }

    function buildTooltip(path) {
        var iso = path.id.toUpperCase();
        var info = countries[iso];

        tooltip.textContent = "";

        tooltip.appendChild(el(
            "map-tooltip-name",
            info ? info.name : (path.getAttribute("aria-label") || iso)
        ));

        if (!info || info.status === "-" || !info.status) {
            tooltip.appendChild(el(
                "map-tooltip-note",
                "Нет данных о визовом режиме"
            ));
            return;
        }

        var statusRow = el("map-tooltip-status");
        var badge = document.createElement("span");
        badge.className = "badge badge-" + slugify(info.status);
        badge.textContent = info.status;
        statusRow.appendChild(badge);
        tooltip.appendChild(statusRow);

        var label = STATUS_LABELS[info.status];
        if (label) {
            tooltip.appendChild(el("map-tooltip-label", label));
        }

        var days = info.days;
        tooltip.appendChild(el(
            "map-tooltip-days",
            days === null || days === undefined
                ? "Без визы: —"
                : "Без визы: " + days + " " + pluralDays(days)
        ));

        if (info.url) {
            tooltip.appendChild(el(
                "map-tooltip-hint",
                "Клик — открыть страну"
            ));
        }
    }

    function placeTooltip(clientX, clientY) {
        var gap = 16;
        var width = tooltip.offsetWidth;
        var height = tooltip.offsetHeight;
        var x = clientX + gap;
        var y = clientY + gap;

        if (x + width > window.innerWidth - 8) {
            x = clientX - width - gap;
        }
        if (y + height > window.innerHeight - 8) {
            y = clientY - height - gap;
        }

        tooltip.style.left = Math.max(8, x) + "px";
        tooltip.style.top = Math.max(8, y) + "px";
    }

    function showTooltip(path, clientX, clientY) {
        buildTooltip(path);
        tooltip.hidden = false;
        placeTooltip(clientX, clientY);
    }

    function hideTooltip() {
        tooltip.hidden = true;
        activePath = null;
    }

    /* ================= страны ================= */

    function initPaths(svg) {
        var paths = svg.querySelectorAll("path[id]");

        Array.prototype.forEach.call(paths, function (path) {
            var iso = path.id.toUpperCase();
            var info = countries[iso];

            path.classList.add("map-country");

            if (info) {
                path.dataset.status = info.status;
                path.dataset.iso = iso;
                path.classList.add("has-data");
                path.setAttribute("aria-label", info.name + ", " + info.status);
            }

            path.addEventListener("mouseenter", function (event) {
                activePath = path;
                showTooltip(path, event.clientX, event.clientY);
            });

            path.addEventListener("mousemove", function (event) {
                if (activePath === path && !tooltip.hidden) {
                    placeTooltip(event.clientX, event.clientY);
                }
            });

            path.addEventListener("mouseleave", function () {
                if (activePath === path) {
                    hideTooltip();
                }
            });

            path.addEventListener("click", function () {
                if (info && info.url) {
                    hideTooltip();
                    window.location.href = info.url;
                }
            });
        });

        svg.addEventListener("mouseleave", hideTooltip);
    }

    /* ================= загрузка ================= */

    function showError() {
        container.textContent = "";
        container.appendChild(el(
            "map-error",
            "Не удалось загрузить карту. Обновите страницу."
        ));
    }

    fetch(container.dataset.svgUrl)
        .then(function (response) {
            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }
            return response.text();
        })
        .then(function (text) {
            var doc = new DOMParser().parseFromString(text, "image/svg+xml");

            if (!doc.documentElement || doc.documentElement.nodeName === "parsererror") {
                throw new Error("bad svg");
            }

            var svg = doc.documentElement;
            svg.setAttribute("class", "map-svg");
            svg.setAttribute("aria-label", "Интерактивная карта мира");
            svg.setAttribute("role", "group");

            container.textContent = "";
            container.appendChild(document.importNode(svg, true));
            container.classList.add("is-ready");

            initPaths(container.querySelector("svg"));
        })
        .catch(showError);
})();
