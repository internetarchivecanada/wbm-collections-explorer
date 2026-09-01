/* Wayback Collection Search Explorer — filtering, sorting, per-tile search, tooltips. */
(function () {
  'use strict';

  /* ---------------------------- theme toggle ---------------------------- */
  var themeBtn = document.getElementById('theme');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var root = document.documentElement;
      var cur = root.getAttribute('data-theme');
      if (!cur) {
        cur = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      var next = cur === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('wce-theme', next); } catch (e) {}
    });
  }

  /* ------------------- search inside one collection ---------------------- */
  // The Wayback route is path-based: /collection-search/<id>/<query>
  document.querySelectorAll('form[data-collection]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var id = form.getAttribute('data-collection');
      var q = form.querySelector('input[name=q]').value.trim();
      var base = 'https://web.archive.org/collection-search/' + encodeURIComponent(id);
      window.open(q ? base + '/' + encodeURIComponent(q) : base, '_blank', 'noopener');
    });
  });

  /* --------------------------- year bar tooltip -------------------------- */
  var bars = document.getElementById('yearbars');
  var tip = document.getElementById('tip');
  if (bars && tip) {
    var show = function (col, x, y) {
      tip.textContent = col.dataset.year + ' · ' + col.dataset.n + ' ' + col.dataset.unit;
      tip.hidden = false;
      var r = tip.getBoundingClientRect();
      tip.style.left = Math.max(8, Math.min(window.innerWidth - r.width - 8, x - r.width / 2)) + 'px';
      tip.style.top = Math.max(8, y - r.height - 12) + 'px';
    };
    bars.addEventListener('mousemove', function (ev) {
      var col = ev.target.closest('.bar-col');
      if (!col) { tip.hidden = true; return; }
      show(col, ev.clientX, ev.clientY);
    });
    bars.addEventListener('mouseleave', function () { tip.hidden = true; });
    bars.addEventListener('focusin', function (ev) {
      var col = ev.target.closest('.bar-col');
      if (!col) return;
      var r = col.getBoundingClientRect();
      show(col, r.left + r.width / 2, r.top + 20);
    });
    bars.addEventListener('focusout', function () { tip.hidden = true; });
  }

  /* ------------------------ filter / sort / view ------------------------- */
  var grid = document.getElementById('grid');
  if (!grid) return;

  var tiles = Array.prototype.slice.call(grid.querySelectorAll('.tile'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('#table tbody tr'));
  var tbody = document.querySelector('#table tbody');
  var qEl = document.getElementById('q');
  var sortEl = document.getElementById('sort');
  var countEl = document.getElementById('count');
  var emptyEl = document.getElementById('empty');
  var tableEl = document.getElementById('table');
  var state = { cat: 'all', q: '', sort: 'count', view: 'tiles' };

  // ?cat=press&sort=stale&view=table&q=hong  — makes a filtered view shareable
  var params = new URLSearchParams(window.location.search);
  ['cat', 'sort', 'view', 'q'].forEach(function (k) {
    var v = params.get(k);
    if (v) state[k] = k === 'q' ? v.toLowerCase() : v;
  });
  var SORT_KEYS = ['count', 'fresh', 'stale', 'title', 'span', 'dead'];
  if (SORT_KEYS.indexOf(state.sort) === -1) state.sort = 'count';
  if (state.view !== 'table') state.view = 'tiles';

  function syncUrl() {
    var p = new URLSearchParams();
    if (state.cat !== 'all') p.set('cat', state.cat);
    if (state.sort !== 'count') p.set('sort', state.sort);
    if (state.view !== 'tiles') p.set('view', state.view);
    if (state.q) p.set('q', state.q);
    var qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : window.location.pathname);
  }

  var num = function (el, key) { return parseFloat(el.dataset[key]); };
  var SORTS = {
    count: function (a, b) { return num(b, 'count') - num(a, 'count'); },
    fresh: function (a, b) { return num(a, 'age') - num(b, 'age'); },
    stale: function (a, b) { return num(b, 'age') - num(a, 'age'); },
    title: function (a, b) { return a.dataset.title.localeCompare(b.dataset.title); },
    span:  function (a, b) { return num(b, 'span') - num(a, 'span'); },
    dead:  function (a, b) { return num(b, 'dead') - num(a, 'dead'); }
  };

  function apply() {
    syncUrl();
    var shown = 0;
    var match = function (el) {
      var okCat = state.cat === 'all' || el.dataset.cat === state.cat;
      var okQ = !state.q || (el.dataset.search || '').indexOf(state.q) !== -1;
      return okCat && okQ;
    };
    tiles.slice().sort(SORTS[state.sort]).forEach(function (el) {
      var ok = match(el);
      el.hidden = !ok;
      if (ok) { shown++; grid.appendChild(el); }
    });
    rows.slice().sort(SORTS[state.sort]).forEach(function (tr) {
      tr.hidden = !match(tr);
      if (!tr.hidden && tbody) tbody.appendChild(tr);
    });

    var total = tiles.length;
    countEl.textContent = shown === total
      ? 'Showing all ' + total.toLocaleString('en-US') + ' collections'
      : 'Showing ' + shown.toLocaleString('en-US') + ' of ' + total.toLocaleString('en-US') + ' collections';
    emptyEl.hidden = shown !== 0;
    grid.hidden = state.view !== 'tiles' || shown === 0;
    tableEl.hidden = state.view !== 'table' || shown === 0;
  }

  document.querySelectorAll('.chip[data-cat]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.chip[data-cat]').forEach(function (o) { o.classList.remove('is-on'); });
      b.classList.add('is-on');
      state.cat = b.dataset.cat;
      apply();
    });
  });
  document.querySelectorAll('.seg[data-view]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.seg[data-view]').forEach(function (o) { o.classList.remove('is-on'); });
      b.classList.add('is-on');
      state.view = b.dataset.view;
      apply();
    });
  });
  qEl.addEventListener('input', function () { state.q = qEl.value.trim().toLowerCase(); apply(); });
  sortEl.addEventListener('change', function () { state.sort = sortEl.value; apply(); });

  // reflect any URL-restored state in the controls, then render
  qEl.value = state.q;
  sortEl.value = state.sort;
  document.querySelectorAll('.chip[data-cat]').forEach(function (b) {
    b.classList.toggle('is-on', b.dataset.cat === state.cat);
  });
  document.querySelectorAll('.seg[data-view]').forEach(function (b) {
    b.classList.toggle('is-on', b.dataset.view === state.view);
  });
  apply();
})();
