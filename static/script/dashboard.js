const getToken  = () => localStorage.getItem('token');
const getUser   = () => localStorage.getItem('username');
const clearAuth = () => localStorage.clear();

if (!getToken()) window.location.href = '/static/html/login.html';

document.getElementById('username-label').textContent = getUser() || 'User';

const authHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`
});

function logout() {
    clearAuth();
    window.location.href = '/static/html/landingpage.html';
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type}`;
    t.style.display = 'flex';
    setTimeout(() => t.style.display = 'none', 3000);
}

const COLOR_MAP = {
    NOTHING: { label: 'No tag',  hex: '#c0a888' },
    GREEN:   { label: 'Green',   hex: '#5cb85c' },
    RED:     { label: 'Red',     hex: '#d9534f' },
    YELLOW:  { label: 'Yellow',  hex: '#e8c84a' },
    BLUE:    { label: 'Blue',    hex: '#4a90e2' },
    PURPLE:  { label: 'Purple',  hex: '#9b59b6' },
};

function openBoard(boardId) {
    localStorage.setItem('boardId', boardId);
    window.location.href = '/static/html/index.html';
}

function renderColorBar(byColor, totalTasks) {
    const bar = document.getElementById('color-bar');
    const legend = document.getElementById('color-legend');
    bar.innerHTML = '';
    legend.innerHTML = '';

    if (!totalTasks) {
        legend.innerHTML = `<span class="no-data">No tasks yet.</span>`;
        return;
    }

    const order = ['NOTHING', 'GREEN', 'YELLOW', 'RED', 'BLUE', 'PURPLE'];
    for (const key of order) {
        const count = byColor[key] || 0;
        if (count === 0) continue;
        const c = COLOR_MAP[key];
        const pct = (count / totalTasks) * 100;

        const seg = document.createElement('div');
        seg.className = 'seg';
        seg.style.flex = String(count);
        seg.style.background = c.hex;
        seg.title = `${c.label}: ${count}`;
        bar.appendChild(seg);

        const item = document.createElement('div');
        item.className = 'legend-item';
        item.innerHTML = `
            <span class="legend-swatch" style="background:${c.hex}"></span>
            <span>${c.label}</span>
            <span class="legend-count">${count} · ${pct.toFixed(0)}%</span>
        `;
        legend.appendChild(item);
    }
}

function renderHighlight(elId, data, kind) {
    const el = document.getElementById(elId);
    if (!data || !data.name) {
        el.innerHTML = `<span class="no-data">No data yet.</span>`;
        return;
    }
    const num = kind === 'tasks' ? data.task_count : data.list_count;
    const word = kind === 'tasks' ? (num === 1 ? 'task' : 'tasks')
                                  : (num === 1 ? 'list' : 'lists');
    el.innerHTML = `
        ${escapeHtml(data.name)}
        <span class="meta">${num} ${word}</span>
    `;
}

function renderBoardsTable(boards) {
    const container = document.getElementById('boards-table');
    if (!boards.length) {
        container.innerHTML = `<span class="no-data">You don't have any boards yet.</span>`;
        return;
    }
    boards.sort((a, b) => b.tasks - a.tasks);

    const rows = [
        `<div class="row head">
            <div>Board</div>
            <div class="col-role">Role</div>
            <div>Lists</div>
            <div>Tasks</div>
        </div>`
    ];

    for (const b of boards) {
        const badge = b.is_owner
            ? `<span class="badge">owner</span>`
            : `<span class="badge shared">shared</span>`;
        rows.push(`
            <div class="row" onclick="openBoard('${b.id}')">
                <div class="board-name">${escapeHtml(b.name)} ${badge}</div>
                <div class="col-role">${b.is_owner ? 'Owner' : 'Member'}</div>
                <div class="num">${b.lists}</div>
                <div class="num">${b.tasks}</div>
            </div>
        `);
    }
    container.innerHTML = rows.join('');
}

function renderCollabs(list) {
    const container = document.getElementById('collabs-list');
    if (!list.length) {
        container.innerHTML = `<span class="no-data">No collaborators yet — add someone to one of your boards.</span>`;
        return;
    }
    container.innerHTML = list.map(u => `<span class="chip">${escapeHtml(u)}</span>`).join('');
}

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

function setText(id, v) {
    document.getElementById(id).textContent = v;
}

async function loadStats() {
    try {
        const res = await fetch('/dashboard/stats', { headers: authHeaders() });
        if (res.status === 401) { logout(); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const s = await res.json();

        setText('stat-boards-total', s.boards_total);
        setText('stat-boards-owned', s.boards_owned);
        setText('stat-boards-shared', s.boards_shared);
        setText('stat-tasks-total', s.total_tasks);
        setText('stat-lists-total', s.total_lists);
        setText('stat-empty-lists', s.empty_lists);
        setText('stat-collabs', s.collaborators_count);

        setText('stat-overdue', s.overdue_tasks);
        setText('stat-upcoming', s.upcoming_tasks);
        setText('stat-with-due', s.tasks_with_due_date);
        setText('stat-no-due', s.tasks_no_due_date);

        setText('stat-avg-tasks-board', s.avg_tasks_per_board);
        setText('stat-avg-lists-board', s.avg_lists_per_board);
        setText('stat-avg-tasks-list', s.avg_tasks_per_list);
        setText('stat-empty-boards', s.empty_boards);

        renderColorBar(s.tasks_by_color || {}, s.total_tasks);
        renderHighlight('biggest-board', s.biggest_board, 'tasks');
        renderHighlight('most-lists-board', s.most_lists_board, 'lists');
        renderBoardsTable(s.boards || []);
        renderCollabs(s.collaborators || []);

        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
    } catch (e) {
        console.error(e);
        document.getElementById('loading').textContent = 'Failed to load stats.';
        showToast('Failed to load dashboard', 'error');
    }
}

loadStats();