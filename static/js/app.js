// State
let currentPage = 1;
let currentSort = 'date';
let sortAsc = false;
let debounceTimer;
let statsData = null;

// --- Helpers ---

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function fmtDate(d) {
    if (!d) return '';
    const p = d.split('-');
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
}

function fmtNumber(n) {
    return n.toLocaleString('fr-FR');
}

const BADGE_COLORS = {
    IFOP:     { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-200' },
    IPSOS:    { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
    ELABE:    { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200' },
    BVA:      { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    ODOXA:    { bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-200' },
    CSA:      { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' },
    HARRIS:   { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
    OPINION:  { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
};

function badgeFor(name) {
    for (const [key, cls] of Object.entries(BADGE_COLORS)) {
        if (name.includes(key)) return cls;
    }
    return { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' };
}

// --- URL State ---

function stateToURL() {
    const p = new URLSearchParams();
    const s = $('search').value;
    const i = $('institut').value;
    const df = $('date-from').value;
    const dt = $('date-to').value;
    if (s) p.set('q', s);
    if (i) p.set('institut', i);
    if (df) p.set('from', df);
    if (dt) p.set('to', dt);
    if (currentPage > 1) p.set('page', currentPage);
    const qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
}

function stateFromURL() {
    const p = new URLSearchParams(location.search);
    if (p.get('q')) $('search').value = p.get('q');
    if (p.get('institut')) $('institut').value = p.get('institut');
    if (p.get('from')) $('date-from').value = p.get('from');
    if (p.get('to')) $('date-to').value = p.get('to');
    if (p.get('page')) currentPage = parseInt(p.get('page')) || 1;
}

function $(id) { return document.getElementById(id); }

function toggleSort() {
    sortAsc = !sortAsc;
    $('sort-icon').innerHTML = sortAsc ? '&uarr;' : '&darr;';
    loadPolls(1);
}

// --- Data loading ---

async function loadStats() {
    const res = await fetch('/api/stats');
    statsData = await res.json();

    // Header subtitle
    $('header-stats').textContent =
        `${fmtNumber(statsData.total)} sondages \u00b7 ${statsData.date_range.min} \u00e0 ${statsData.date_range.max} \u00b7 ${Object.keys(statsData.by_institut).length} instituts`;

    // Populate institute dropdown
    const sel = $('institut');
    const current = sel.value;
    sel.innerHTML = '<option value="">Tous les instituts</option>';
    const sorted = Object.entries(statsData.by_institut).sort((a, b) => b[1] - a[1]);
    for (const [name] of sorted) {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        sel.appendChild(opt);
    }
    sel.value = current;

    // Stat cards
    renderStats(sorted);

    // Year chart
    renderYearChart(statsData.by_year);
}

function renderStats(sorted) {
    const grid = $('stats-grid');
    grid.innerHTML = `
        <div class="col-span-full sm:col-span-1 bg-accent rounded-xl p-5 text-white cursor-pointer hover:bg-accent-dark transition-colors"
             onclick="resetFilters()">
            <div class="text-xs font-semibold uppercase tracking-wider text-white/60">Total</div>
            <div class="text-3xl font-extrabold mt-1 tracking-tight">${fmtNumber(statsData.total)}</div>
        </div>
    ` + sorted.map(([name, count]) => {
        const b = badgeFor(name);
        return `
        <div class="bg-white rounded-xl border border-gray-100 p-4 hover:shadow-md hover:border-gray-200 transition-all cursor-pointer group"
             onclick="pickInstitut('${esc(name)}')">
            <div class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 group-hover:text-gray-500">${esc(name)}</div>
            <div class="text-xl font-bold mt-0.5 text-gray-800">${fmtNumber(count)}</div>
        </div>`;
    }).join('');
}

function renderYearChart(byYear) {
    const container = $('year-chart');
    const years = Object.keys(byYear).map(Number).sort();
    if (years.length === 0) return;

    const counts = years.map(y => byYear[y]);
    const max = Math.max(...counts);

    container.innerHTML = `
        <div class="flex items-end gap-[3px] h-20">
            ${years.map((y, i) => {
                const h = Math.max(4, (counts[i] / max) * 100);
                return `<div class="group relative flex-1 flex flex-col items-center justify-end h-full">
                    <div class="absolute -top-7 bg-gray-800 text-white text-[10px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                        ${y}: ${fmtNumber(counts[i])}
                    </div>
                    <div class="w-full rounded-sm bg-accent/20 hover:bg-accent/40 transition-colors" style="height:${h}%"></div>
                </div>`;
            }).join('')}
        </div>
        <div class="flex justify-between mt-1.5 text-[9px] text-gray-400 font-medium">
            <span>${years[0]}</span>
            <span>${years[years.length - 1]}</span>
        </div>
    `;
}

async function loadPolls(page = 1) {
    currentPage = page;
    const perPage = $('per-page').value;
    const params = new URLSearchParams({
        page,
        per_page: perPage,
        search: $('search').value,
        institut: $('institut').value,
        date_from: $('date-from').value,
        date_to: $('date-to').value,
        sort_asc: sortAsc ? '1' : '0',
    });

    stateToURL();
    updateFilterPills();

    const tbody = $('polls-body');

    const res = await fetch(`/api/polls?${params}`);
    const data = await res.json();

    const footer = $('table-footer');

    if (data.polls.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" class="px-5 py-16 text-center">
                    <div class="text-gray-300 text-4xl mb-3">&#128269;</div>
                    <p class="text-gray-400 text-sm">Aucun sondage trouv\u00e9</p>
                </td>
            </tr>`;
        footer.classList.add('hidden');
    } else {
        tbody.innerHTML = data.polls.map(p => {
            const b = badgeFor(p.institut);
            return `
            <tr class="group hover:bg-gray-50/80 transition-colors">
                <td class="px-5 py-3 text-sm text-gray-400 tabular-nums whitespace-nowrap">${fmtDate(p.date) || '<span class="text-gray-300">\u2014</span>'}</td>
                <td class="px-5 py-3">
                    <span class="inline-flex px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${b.bg} ${b.text} ${b.border}">${esc(p.institut)}</span>
                </td>
                <td class="px-5 py-3 text-sm text-gray-700">
                    ${p.link
                        ? `<a href="${esc(p.link)}" target="_blank" rel="noopener" class="hover:text-accent transition-colors group-hover:underline underline-offset-2 decoration-gray-300">${esc(p.subject)}<span class="inline-block ml-1 opacity-0 group-hover:opacity-40 transition-opacity text-xs">\u2197</span></a>`
                        : esc(p.subject)}
                </td>
            </tr>`;
        }).join('');
        footer.classList.remove('hidden');
        renderPager(data);
    }
}

function renderPager(data) {
    const s = (data.page - 1) * data.per_page + 1;
    const e = Math.min(data.page * data.per_page, data.total);
    $('page-info').textContent = `${fmtNumber(s)}\u2013${fmtNumber(e)} sur ${fmtNumber(data.total)}`;

    const tp = data.total_pages, cp = data.page;
    const pages = [1];
    if (cp > 3) pages.push('...');
    for (let i = Math.max(2, cp - 1); i <= Math.min(tp - 1, cp + 1); i++) pages.push(i);
    if (cp < tp - 2) pages.push('...');
    if (tp > 1) pages.push(tp);

    let h = `<button ${cp <= 1 ? 'disabled' : ''} onclick="loadPolls(${cp - 1})" class="pager-btn">\u2039</button>`;
    for (const p of pages) {
        h += p === '...'
            ? `<button disabled class="pager-btn">\u2026</button>`
            : `<button class="pager-btn ${p === cp ? 'active' : ''}" onclick="loadPolls(${p})">${p}</button>`;
    }
    h += `<button ${cp >= tp ? 'disabled' : ''} onclick="loadPolls(${cp + 1})" class="pager-btn">\u203A</button>`;
    $('pager').innerHTML = h;
}

// --- Filters ---

function updateFilterPills() {
    const el = $('filter-pills');
    const tags = [];
    const s = $('search').value;
    const i = $('institut').value;
    const df = $('date-from').value;
    const dt = $('date-to').value;

    if (s) tags.push({ text: `\u00ab ${s} \u00bb`, field: 'search' });
    if (i) tags.push({ text: i, field: 'institut' });
    if (df) tags.push({ text: `Depuis ${fmtDate(df)}`, field: 'date-from' });
    if (dt) tags.push({ text: `Jusqu'au ${fmtDate(dt)}`, field: 'date-to' });

    if (tags.length === 0) {
        el.innerHTML = '';
        return;
    }

    el.innerHTML = tags.map(t => `
        <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-accent/5 border border-accent/10 rounded-full text-xs font-medium text-accent">
            ${esc(t.text)}
            <button onclick="clearField('${t.field}')" class="text-accent/40 hover:text-accent transition-colors">&times;</button>
        </span>
    `).join('');
}

function clearField(field) {
    $(field).value = '';
    loadPolls(1);
}

function pickInstitut(name) {
    const sel = $('institut');
    sel.value = name;
    loadPolls(1);
}

function resetFilters() {
    $('search').value = '';
    $('institut').value = '';
    $('date-from').value = '';
    $('date-to').value = '';
    loadPolls(1);
}

// --- Events ---

document.addEventListener('DOMContentLoaded', () => {
    stateFromURL();

    $('search').addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadPolls(1), 300);
    });
    $('institut').addEventListener('change', () => loadPolls(1));
    $('date-from').addEventListener('change', () => loadPolls(1));
    $('date-to').addEventListener('change', () => loadPolls(1));
    $('per-page').addEventListener('change', () => loadPolls(1));

    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            $('search').focus();
        }
        if (e.key === 'Escape') document.activeElement.blur();
    });

    loadStats();
    loadPolls(currentPage);
});
