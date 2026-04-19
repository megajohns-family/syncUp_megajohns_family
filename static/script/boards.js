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

async function loadBoards() {
    const res = await fetch('/boards', { headers: authHeaders() });
    if (res.status === 401) { logout(); return; }
    const boards = await res.json();
    const container = document.getElementById('boards-list');

    if (!boards.length) {
        container.innerHTML = `<p style="color:var(--muted)">No boards yet. Create one above.</p>`;
        return;
    }

    container.innerHTML = boards.map(b => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;margin-bottom:12px;background:var(--surface);border-radius:12px;cursor:pointer;" onclick="openBoard('${b.id}')">
            <div>
                <div style="font-weight:500;">${b.name || b.id}</div>
                <div style="font-size:12px;color:var(--muted);">owner: ${b.owner}</div>
            </div>
            <span style="font-size:20px;">→</span>
        </div>
    `).join('');
}

async function createBoard() {
    const input = document.getElementById('new-board-name');
    const name = input.value.trim();
    if (!name) return;
    input.value = '';
    const res = await fetch('/boards', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ name })
    });
    if (res.ok) { showToast('Board created ✓'); loadBoards(); }
    else showToast('Failed to create board', 'error');
}

function openBoard(boardId) {
    localStorage.setItem('boardId', boardId);
    window.location.href = '/static/html/index.html';
}

loadBoards();