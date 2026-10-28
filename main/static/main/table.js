// Интерактив таблицы:
//  - горизонтальное перетаскивание (drag-to-scroll);
//  - изменение ширины колонок за разделитель в заголовке (как в Excel).

(function () {
    "use strict";

    var DRAG_THRESHOLD = 6;   // px, чтобы обычный клик не считался перетаскиванием
    var MIN_COL_WIDTH = 80;   // px, уже колонку не сжать

    // Ширины колонок запоминаем в памяти страницы, чтобы фильтры/sorting
    // через HTMX не сбрасывали ручную настройку.
    var savedWidths = null;

    /* ================= drag-to-scroll ================= */

    function setupDragScroll(el) {
        if (el.dataset.dragScroll === "1") {
            return;
        }
        el.dataset.dragScroll = "1";

        var isDown = false;
        var moved = false;
        var startX = 0;
        var startScroll = 0;

        function updateScrollable() {
            el.classList.toggle(
                "is-scrollable",
                el.scrollWidth > el.clientWidth
            );
        }

        el.addEventListener("mousedown", function (e) {
            if (e.button !== 0) {
                return;
            }

            // За разделитель колонки тянет ресайзер, а не скролл
            if (e.target.closest(".col-resizer")) {
                return;
            }

            isDown = true;
            moved = false;
            startX = e.pageX;
            startScroll = el.scrollLeft;
        });

        window.addEventListener("mousemove", function (e) {
            if (!isDown) {
                return;
            }

            var dx = e.pageX - startX;

            if (Math.abs(dx) > DRAG_THRESHOLD) {
                moved = true;
                el.classList.add("is-dragging");
            }

            if (moved) {
                e.preventDefault();
                el.scrollLeft = startScroll - dx;
            }
        });

        function stopDrag() {
            if (!isDown) {
                return;
            }

            isDown = false;
            el.classList.remove("is-dragging");
        }

        window.addEventListener("mouseup", stopDrag);
        window.addEventListener("blur", stopDrag);

        // После перетаскивания не даём клику открыть страну/сортировку
        el.addEventListener("click", function (e) {
            if (moved) {
                e.preventDefault();
                e.stopPropagation();
                moved = false;
            }
        }, true);

        // Убираем нативный drag ссылок и картинок
        el.addEventListener("dragstart", function (e) {
            e.preventDefault();
        });

        updateScrollable();
        window.addEventListener("resize", updateScrollable);

        el._updateScrollable = updateScrollable;
    }

    /* ================= изменение ширины колонок ================= */

    function applyWidths(table, widths) {
        var cols = table.querySelectorAll("colgroup col");
        if (cols.length !== widths.length) {
            return;
        }

        table.style.tableLayout = "fixed";
        table.style.width = widths.reduce(function (a, b) {
            return a + b;
        }, 0) + "px";

        widths.forEach(function (width, i) {
            cols[i].style.width = width + "px";
        });
    }

    function setupResizable(table) {
        var ths = table.querySelectorAll("thead th");
        if (ths.length < 2) {
            return;
        }

        var colgroup = table.querySelector("colgroup");
        if (!colgroup) {
            colgroup = document.createElement("colgroup");
            for (var i = 0; i < ths.length; i++) {
                colgroup.appendChild(document.createElement("col"));
            }
            table.insertBefore(colgroup, table.firstChild);
        }

        // Ручки-разделители на всех колонках кроме последней
        for (var j = 0; j < ths.length; j++) {
            if (j < ths.length - 1 && !ths[j].querySelector(".col-resizer")) {
                var handle = document.createElement("span");
                handle.className = "col-resizer";
                ths[j].appendChild(handle);
            }
        }

        // Если пользователь уже менял ширины — применяем их к новой таблице
        if (savedWidths && savedWidths.length === ths.length) {
            applyWidths(table, savedWidths);
        }
    }

    var resize = null;

    document.addEventListener("mousedown", function (e) {
        var handle = e.target.closest(".col-resizer");
        if (!handle) {
            return;
        }

        var th = handle.closest("th");
        var table = th ? th.closest("table") : null;
        if (!th || !table) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        var ths = Array.prototype.slice.call(table.querySelectorAll("thead th"));
        var index = ths.indexOf(th);
        var cols = table.querySelectorAll("colgroup col");
        if (index < 0 || cols.length !== ths.length) {
            return;
        }

        var widths = ths.map(function (cell) {
            return cell.getBoundingClientRect().width;
        });

        savedWidths = widths.slice();
        applyWidths(table, widths);

        resize = {
            col: cols[index],
            index: index,
            startX: e.pageX,
            startWidth: widths[index],
            table: table
        };

        document.body.classList.add("is-col-resizing");
    });

    document.addEventListener("mousemove", function (e) {
        if (!resize) {
            return;
        }

        e.preventDefault();

        var dx = e.pageX - resize.startX;
        var width = Math.max(MIN_COL_WIDTH, resize.startWidth + dx);

        resize.col.style.width = width + "px";
        savedWidths[resize.index] = width;

        resize.table.style.width = savedWidths.reduce(function (a, b) {
            return a + b;
        }, 0) + "px";
    });

    document.addEventListener("mouseup", function () {
        if (!resize) {
            return;
        }

        resize = null;
        document.body.classList.remove("is-col-resizing");
    });

    /* ================= инициализация ================= */

    function init() {
        document.querySelectorAll(".table-wrapper").forEach(function (el) {
            setupDragScroll(el);

            if (el._updateScrollable) {
                el._updateScrollable();
            }

            el.querySelectorAll("table").forEach(setupResizable);
        });
    }

    init();
    document.body.addEventListener("htmx:afterSwap", init);
})();
