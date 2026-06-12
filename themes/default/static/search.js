/* Navbar search: fetches /search?q= and renders a results dropdown.
 *
 * Works with the shared _search.html partial in both modes:
 *   button — [data-search="button"]: a toggle button opens the dropdown
 *            (which contains the input).
 *   input  — [data-search="input"]: the input is inline in the navbar and
 *            the dropdown shows results only.
 *
 * Results are rendered exclusively with createElement/textContent — never
 * innerHTML — because titles/excerpts/tags are author-supplied content and
 * Jinja autoescaping does not protect JSON-to-DOM rendering.
 */
(function () {
    'use strict';

    var DEBOUNCE_MS = 200;
    var MIN_CHARS = 2;

    function formatDate(iso) {
        // Parse as local date parts; new Date("YYYY-MM-DD") is UTC and can
        // shift a day in negative-offset timezones.
        var parts = iso.split('-');
        var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    }

    function initSearch(root) {
        var mode = root.getAttribute('data-search') || 'button';
        var toggle = root.querySelector('.search-toggle');
        var input = root.querySelector('.search-input');
        var dropdown = root.querySelector('.search-dropdown');
        var list = root.querySelector('.search-results');
        var empty = root.querySelector('.search-empty');
        if (!input || !dropdown || !list) return;

        var debounceTimer = null;
        var controller = null;
        var activeIndex = -1;

        function setExpanded(expanded) {
            input.setAttribute('aria-expanded', expanded ? 'true' : 'false');
            if (toggle) toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        }

        function openDropdown() {
            dropdown.hidden = false;
            setExpanded(true);
        }

        function closeDropdown() {
            dropdown.hidden = true;
            setExpanded(false);
            setActive(-1);
        }

        function clearResults() {
            list.textContent = '';
            if (empty) empty.hidden = true;
            setActive(-1);
        }

        function options() {
            return list.querySelectorAll('[role="option"]');
        }

        function setActive(index) {
            var opts = options();
            if (activeIndex >= 0 && opts[activeIndex]) {
                opts[activeIndex].classList.remove('is-active');
            }
            activeIndex = index;
            if (index >= 0 && opts[index]) {
                opts[index].classList.add('is-active');
                input.setAttribute('aria-activedescendant', opts[index].id);
                opts[index].scrollIntoView({ block: 'nearest' });
            } else {
                input.removeAttribute('aria-activedescendant');
            }
        }

        function renderResults(results) {
            clearResults();
            if (results.length === 0) {
                if (empty) empty.hidden = false;
                return;
            }
            results.forEach(function (result, i) {
                var item = document.createElement('li');
                item.setAttribute('role', 'option');
                item.id = 'search-opt-' + i;

                var link = document.createElement('a');
                link.className = 'search-result-link';
                link.href = result.url;

                var title = document.createElement('span');
                title.className = 'search-result-title';
                title.textContent = result.title;
                link.appendChild(title);

                var meta = document.createElement('span');
                meta.className = 'search-result-meta';
                if (result.date) {
                    var date = document.createElement('span');
                    date.className = 'search-result-date';
                    date.textContent = formatDate(result.date);
                    meta.appendChild(date);
                }
                if (result.draft) {
                    var badge = document.createElement('span');
                    badge.className = 'search-result-draft';
                    badge.textContent = 'draft';
                    meta.appendChild(badge);
                }
                if (meta.childNodes.length > 0) link.appendChild(meta);

                if (result.excerpt) {
                    var excerpt = document.createElement('span');
                    excerpt.className = 'search-result-excerpt';
                    excerpt.textContent = result.excerpt;
                    link.appendChild(excerpt);
                }

                item.appendChild(link);
                list.appendChild(item);
            });
        }

        function runSearch(query) {
            if (controller) controller.abort();
            controller = new AbortController();
            fetch('/search?q=' + encodeURIComponent(query), { signal: controller.signal })
                .then(function (resp) { return resp.json(); })
                .then(function (data) {
                    // Guard against out-of-order responses: only render if
                    // the input still shows the query this response answers.
                    if (input.value.trim() !== data.query.trim()) return;
                    renderResults(data.results);
                    openDropdown();
                })
                .catch(function (err) {
                    if (err.name !== 'AbortError') clearResults();
                });
        }

        input.addEventListener('input', function () {
            var query = input.value.trim();
            if (debounceTimer) clearTimeout(debounceTimer);
            if (query.length < MIN_CHARS) {
                clearResults();
                // Button mode keeps its panel open while focused; input
                // mode hides the results-only dropdown.
                if (mode === 'input') closeDropdown();
                return;
            }
            debounceTimer = setTimeout(function () { runSearch(query); }, DEBOUNCE_MS);
        });

        input.addEventListener('focus', function () {
            if (mode === 'input' && input.value.trim().length >= MIN_CHARS) {
                openDropdown();
            }
        });

        input.addEventListener('keydown', function (e) {
            var opts = options();
            if (e.key === 'ArrowDown' && opts.length > 0) {
                e.preventDefault();
                setActive(activeIndex < opts.length - 1 ? activeIndex + 1 : 0);
            } else if (e.key === 'ArrowUp' && opts.length > 0) {
                e.preventDefault();
                setActive(activeIndex > 0 ? activeIndex - 1 : opts.length - 1);
            } else if (e.key === 'Enter') {
                var target = activeIndex >= 0 ? opts[activeIndex] : opts[0];
                var link = target && target.querySelector('a');
                if (link) {
                    e.preventDefault();
                    window.location.href = link.href;
                }
            }
        });

        if (toggle) {
            toggle.addEventListener('click', function () {
                if (dropdown.hidden) {
                    openDropdown();
                    input.focus();
                } else {
                    closeDropdown();
                }
            });
        }

        document.addEventListener('keydown', function (e) {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                if (mode === 'button') openDropdown();
                input.focus();
            } else if (e.key === 'Escape' && !dropdown.hidden) {
                closeDropdown();
                input.blur();
            }
        });

        document.addEventListener('click', function (e) {
            if (!root.contains(e.target)) closeDropdown();
        });
    }

    function init() {
        document.querySelectorAll('[data-search]').forEach(initSearch);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
