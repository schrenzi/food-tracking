document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("food-search");
    const foodIdInput = document.getElementById("food-id");
    const resultsDiv = document.getElementById("food-results");

    if (!searchInput) return;

    let debounceTimer;

    searchInput.addEventListener("input", function () {
        const q = this.value.trim();
        clearTimeout(debounceTimer);

        if (q.length < 1) {
            resultsDiv.style.display = "none";
            return;
        }

        debounceTimer = setTimeout(function () {
            fetch("/api/foods/search?q=" + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (foods) {
                    resultsDiv.innerHTML = "";
                    if (foods.length === 0) {
                        resultsDiv.innerHTML =
                            '<div class="list-group-item text-muted">Keine Ergebnisse</div>';
                        resultsDiv.style.display = "block";
                        return;
                    }
                    foods.forEach(function (f) {
                        const item = document.createElement("button");
                        item.type = "button";
                        item.className = "list-group-item list-group-item-action";
                        item.innerHTML =
                            "<strong>" + escapeHtml(f.name) + "</strong>" +
                            (f.brand ? " <small class='text-muted'>(" + escapeHtml(f.brand) + ")</small>" : "") +
                            " <span class='float-end text-muted'>" + f.calories + " kcal</span>";
                        item.addEventListener("click", function () {
                            searchInput.value = f.name;
                            foodIdInput.value = f.id;
                            resultsDiv.style.display = "none";
                        });
                        resultsDiv.appendChild(item);
                    });
                    resultsDiv.style.display = "block";
                });
        }, 250);
    });

    document.addEventListener("click", function (e) {
        if (!resultsDiv.contains(e.target) && e.target !== searchInput) {
            resultsDiv.style.display = "none";
        }
    });

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }
});
