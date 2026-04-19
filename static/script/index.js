const API = '';
const boardId = localStorage.getItem('boardId') || 'tasks_test';
const getToken  = () => localStorage.getItem('token');
const getUser   = () => localStorage.getItem('username');
const clearAuth = () => localStorage.clear();

window.onload = () => {
    if (!getToken()) return window.location.href = '/static/html/login.html';
    document.getElementById('username-label').textContent = getUser() || 'User';
    loadLists();
};

// function requireBoard() {
//     const boardId = localStorage.getItem('boardId');

//     if (!boardId || boardId === "null" || boardId === "undefined") {
//         console.warn("No board selected");
//         window.location.replace('/static/html/boards.html');
//         return null;
//     }

//     return boardId;
// }
// function getBoardId() {
//     return localStorage.getItem('boardId');
// }

// window.onload = () => {
//     if (!getToken()) {
//         window.location.replace('/static/html/login.html');
//         return;
//     }

    // const boardId = requireBoard();
    // if (!boardId) {
    //     showToast("No board selected", "error");

    //     setTimeout(() => {
    //         window.location.replace('/static/html/boards.html');
    //     }, 800);

    //     return;
    // }

//     document.getElementById('username-label').textContent = getUser() || 'User';
//     loadLists();
// };

function logout() {
    clearAuth();
    window.location.href = '/static/html/landingpage.html';
}

const authHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`
});

async function apiFetch(path, opts = {}) {
    const res = await fetch(API + path, { headers: authHeaders(), ...opts });
    if (res.status === 401) logout();
    return res;
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `toast ${type}`;
    t.style.display = 'flex';
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.style.display = 'none', 3000);
}

function showConfirm({ title, body, icon = '🗑️', confirmLabel = 'Delete' }) {
    return new Promise(resolve => {
        const overlay   = document.getElementById('modal-overlay');
        const btnOk     = document.getElementById('modal-confirm');
        const btnCancel = document.getElementById('modal-cancel');

        document.getElementById('modal-icon').textContent  = icon;
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').textContent  = body;
        btnOk.textContent = confirmLabel;

        overlay.classList.add('open');

        const close = result => {
            overlay.classList.remove('open');
            btnOk.removeEventListener('click', onOk);
            btnCancel.removeEventListener('click', onCancel);
            resolve(result);
        };
        const onOk     = () => close(true);
        const onCancel = () => close(false);

        btnOk.addEventListener('click', onOk);
        btnCancel.addEventListener('click', onCancel);
        overlay.addEventListener('click', e => {
            if (e.target === overlay) close(false);
        }, { once: true });
    });
}


const COLORS = [
    { id: 'NOTHING', label: 'None',   hex: null },
    { id: 'GREEN',   label: 'Green',  hex: '#5cb85c' },
    { id: 'RED',     label: 'Red',    hex: '#d9534f' },
    { id: 'YELLOW',  label: 'Yellow', hex: '#f0ad4e' },
    { id: 'BLUE',    label: 'Blue',   hex: '#4285f4' },
    { id: 'PURPLE',  label: 'Purple', hex: '#9b59b6' },
];


async function loadLists() {
    document.getElementById('loading').style.display = '';
    document.getElementById('lists-grid').innerHTML = '';
    const res = await apiFetch(`/boards/${boardId}/lists`);
    document.getElementById('loading').style.display = 'none';
    if (!res) return;
    const data = await res.json();
    renderLists(data);
}

function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


let dragTaskId = null;
let dragListId = null;

function renderLists(data) {
    const grid = document.getElementById('lists-grid');
    grid.innerHTML = '';
    const entries = Object.entries(data || {});

    if (!entries.length) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:120px 20px;color:var(--muted);font-size:18px;">
            No lists yet.<br>Create one above 👆
        </div>`;
        return;
    }


    for (const [id, list] of entries) {
        grid.appendChild(makeCard(id, list));
    }

    initListDragDrop();
}


function makeCard(listId, list) {
    const card = document.createElement('div');
    card.className = 'list-card';
    card.dataset.listId = listId;

    const tasks     = list.tasks ? Object.entries(list.tasks) : [];
    const taskCount = tasks.length;

    const tasksHtml = taskCount
        ? tasks.map(([tid, t]) => makeTaskHtml(tid, t, listId)).join('')
        : `<div class="empty-state">No tasks yet — drop one here or add below</div>`;

    card.innerHTML = `
        <div class="list-header">
            <div class="list-header-left">
                <span class="drag-handle" title="Drag to reorder">⠿</span>
                <span class="list-name">${esc(list.name)}</span>
                ${taskCount ? `<span class="task-count">${taskCount}</span>` : ''}
            </div>
            <button class="delete-list-btn"
                    onclick="confirmDeleteList('${listId}','${esc(list.name)}')"
                    title="Delete list">✕</button>
        </div>
        <div class="task-list" data-list-id="${listId}">
            ${tasksHtml}
        </div>
        <div class="new-task-form">
            <input type="text" id="task-input-${listId}"
                   placeholder="New task…"
                   onkeydown="if(event.key==='Enter') createTask('${listId}')">
            <button onclick="createTask('${listId}')">+</button>
        </div>`;

    setupTaskDropZone(card.querySelector('.task-list'), listId);
    return card;
}


function makeTaskHtml(tid, t, listId) {
    const color    = (t.color_tag || 'NOTHING').toUpperCase();
    const colorObj = COLORS.find(c => c.id === color) || COLORS[0];
    const dotStyle = colorObj.hex
        ? `background:${colorObj.hex};`
        : `background:transparent;border:2px solid #c0a888;`;

    const descText = t.description || '';
    const descHtml = descText
        ? `<div class="task-desc" data-task-id="${tid}" data-field="description" contenteditable="false">${esc(descText)}</div>`
        : `<div class="task-desc task-desc-placeholder" data-task-id="${tid}" data-field="description" contenteditable="false">Add description…</div>`;

    const swatchNone = `background:transparent;border:2px solid #c0a888;border-radius:50%;display:block;width:11px;height:11px;`;

    return `
    <div class="task-item" draggable="true" data-task-id="${tid}" data-list-id="${listId}">
        <div class="color-dot-wrap">
            <div class="color-dot color-${color}" style="${dotStyle}"
                 onclick="toggleColorDropdown(event,'${tid}')"></div>
            <div class="color-dropdown" id="color-dd-${tid}">
                ${COLORS.map(c => `
                    <button class="color-option ${c.id === color ? 'active' : ''}"
                            onclick="setColor('${tid}','${c.id}')">
                        <span class="swatch" style="${c.hex ? `background:${c.hex};` : swatchNone}"></span>
                        ${c.label}
                    </button>`).join('')}
            </div>
        </div>
        <div class="task-text">
            <div class="task-name" data-task-id="${tid}" data-field="name"
                 contenteditable="false">${esc(t.name)}</div>
            ${descHtml}
        </div>
        <div class="task-actions">
            <button class="task-btn"
                    onclick="confirmDeleteTask('${tid}','${esc(t.name)}')"
                    title="Delete task">✕</button>
        </div>
    </div>`;
}


function toggleColorDropdown(e, taskId) {
    e.stopPropagation();
    const dd = document.getElementById(`color-dd-${taskId}`);
    const wasOpen = dd.classList.contains('open');
    closeAllDropdowns();
    if (!wasOpen) dd.classList.add('open');
}
function closeAllDropdowns() {
    document.querySelectorAll('.color-dropdown.open').forEach(d => d.classList.remove('open'));
}
document.addEventListener('click', closeAllDropdowns);

async function setColor(taskId, colorId) {
    closeAllDropdowns();
    const res = await apiFetch(`/boards/${boardId}/tasks/${taskId}`, {
        method: 'PATCH',
        body: JSON.stringify({ color_tag: colorId })
    });
    if (res?.ok) { showToast('Color updated', 'success'); loadLists(); }
    else showToast('Failed to update color', 'error');
}

document.addEventListener('dblclick', e => {
    const el = e.target.closest('[data-field]');
    if (!el || el.contentEditable === 'true') return;

    el.classList.remove('task-desc-placeholder');
    el.contentEditable = 'true';
    el.focus();

    const range = document.createRange();
    range.selectNodeContents(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);

    const taskId   = el.dataset.taskId;
    const field    = el.dataset.field;
    const original = el.textContent;

    const commit = async () => {
        el.contentEditable = 'false';
        const newVal = el.textContent.trim();
        if (newVal === original) return;

        const body = field === 'name'
            ? { name: newVal || original }
            : { description: newVal };

        const res = await apiFetch(`/boards/${boardId}/tasks/${taskId}`, {
            method: 'PATCH',
            body: JSON.stringify(body)
        });

        if (res?.ok) {
            showToast('Task updated', 'success');
            if (!newVal && field === 'description') {
                el.textContent = 'Add description…';
                el.classList.add('task-desc-placeholder');
            }
        } else {
            el.textContent = original;
            showToast('Failed to update', 'error');
        }
    };

    el.addEventListener('blur', commit, { once: true });
    el.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' && field === 'name') { ev.preventDefault(); el.blur(); }
        if (ev.key === 'Escape') { el.textContent = original; el.blur(); }
    });
});

document.addEventListener('dragstart', e => {
    const item = e.target.closest('.task-item');
    if (!item) return;
    dragTaskId = item.dataset.taskId;
    item.classList.add('task-dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', `task:${dragTaskId}`);
});

document.addEventListener('dragend', e => {
    const item = e.target.closest('.task-item');
    if (item) item.classList.remove('task-dragging');
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
    dragTaskId = null;
});

function setupTaskDropZone(el, listId) {
    el.addEventListener('dragover', e => {
        if (!dragTaskId) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        el.closest('.list-card').classList.add('drag-over');
    });

    el.addEventListener('dragleave', e => {
        if (!el.contains(e.relatedTarget)) {
            el.closest('.list-card').classList.remove('drag-over');
        }
    });

    el.addEventListener('drop', async e => {
        e.preventDefault();
        el.closest('.list-card').classList.remove('drag-over');
        if (!dragTaskId) return;

        const sourceEl     = document.querySelector(`.task-item[data-task-id="${dragTaskId}"]`);
        const sourceListId = sourceEl?.dataset.listId;


        if (String(sourceListId) === String(listId)) return;

        const res = await apiFetch(`/boards/${boardId}/tasks/${dragTaskId}/move`, {
        method: 'POST',
        body: JSON.stringify({ target_list_id: parseInt(listId) })
        });
        if (res?.ok) { showToast('Task moved ✓', 'success'); loadLists(); }
        else showToast('Could not move task', 'error');
    });
}

function initListDragDrop() {
    const grid = document.getElementById('lists-grid');


    grid.querySelectorAll('.drag-handle').forEach(handle => {
        handle.addEventListener('mousedown', () => {
            handle.closest('.list-card').draggable = true;
        });
        handle.addEventListener('mouseup', () => {
            handle.closest('.list-card').draggable = false;
        });
    });

    grid.addEventListener('dragstart', e => {
        const card = e.target.closest('.list-card[draggable="true"]');
        if (!card || dragTaskId) return; 
        dragListId = card.dataset.listId;
        card.classList.add('dragging-list');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', `list:${dragListId}`);
        e.stopPropagation();
    });

    grid.addEventListener('dragover', e => {
        if (!dragListId) return;
        const card = e.target.closest('.list-card');
        if (!card || card.dataset.listId === dragListId) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    });

    grid.addEventListener('drop', async e => {
        if (!dragListId) return;
        e.preventDefault();

        const targetCard = e.target.closest('.list-card');
        if (!targetCard || targetCard.dataset.listId === dragListId) {
            cleanupListDrag();
            return;
        }

        const cards   = [...grid.querySelectorAll('.list-card')];
        const srcCard = cards.find(c => c.dataset.listId === dragListId);
        if (!srcCard) { cleanupListDrag(); return; }

        const srcIdx = cards.indexOf(srcCard);
        const tgtIdx = cards.indexOf(targetCard);


        if (srcIdx < tgtIdx) targetCard.after(srcCard);
        else                  targetCard.before(srcCard);

        const newOrder = [...grid.querySelectorAll('.list-card')]
            .map(c => parseInt(c.dataset.listId));

        cleanupListDrag();


        const res = await apiFetch(`/boards/${boardId}/lists/order`, {
            method: 'PUT',
            body: JSON.stringify({ order: newOrder })
        });
        if (!res?.ok) {
            showToast('Could not save list order', 'error');
            loadLists(); 
        }
    });

    grid.addEventListener('dragend', cleanupListDrag);

    function cleanupListDrag() {
        grid.querySelectorAll('.dragging-list').forEach(c => {
            c.classList.remove('dragging-list');
            c.draggable = false;
        });
        dragListId = null;
    }
}


async function createList() {
    const input = document.getElementById('new-list-name');
    const name  = input.value.trim();
    if (!name) return;
    input.value = '';
    const res = await apiFetch(`/boards/${boardId}/lists`, {
    method: 'POST',
    body: JSON.stringify({ name })
});
    if (res?.ok)  { showToast('List created ✓', 'success'); loadLists(); }
    else showToast('Failed to create list', 'error');
}

async function confirmDeleteList(listId, listName) {
    const ok = await showConfirm({
        title: 'Delete list?',
        body: `"${listName}" and all its tasks will be permanently removed.`,
        icon: '🗂️',
        confirmLabel: 'Delete list',
    });
    if (!ok) return;
    const res = await apiFetch(`/boards/${boardId}/lists/${listId}`, {method: 'DELETE'});
    if (res?.ok)  { showToast('List deleted', 'info'); loadLists(); }
    else showToast('Failed to delete list', 'error');
}

async function createTask(listId) {
    const input = document.getElementById(`task-input-${listId}`);
    const name  = input.value.trim();
    if (!name) return;
    input.value = '';
    const res = await apiFetch(`/boards/${boardId}/lists/${listId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ name, description: '' })
    });
    if (res?.ok)  { showToast('Task added ✓', 'success'); loadLists(); }
    else showToast('Failed to add task', 'error');
}

async function confirmDeleteTask(taskId, taskName) {
    const ok = await showConfirm({
        title: 'Delete task?',
        body: `"${taskName}" will be permanently removed.`,
        icon: '🗑️',
        confirmLabel: 'Delete task',
    });
    if (!ok) return;
    const res = await apiFetch(`/boards/${boardId}/tasks/${taskId}`, { method: 'DELETE' });
    if (res?.ok)  { showToast('Task deleted', 'info'); loadLists(); }
    else showToast('Failed to delete task', 'error');
}

const ws = new WebSocket(`ws://${location.host}/ws/${boardId}?token=${getToken()}`);

ws.onmessage = (e) => {
    const { event } = JSON.parse(e.data);
    loadLists();
};

ws.onclose = () => {
    setTimeout(() => location.reload(), 2000);
};

ws.onmessage = (e) => {
    const { event, data } = JSON.parse(e.data);
    loadLists();

    const messages_success = {
        color_updated: `Color updated`,
        list_created: `New list added`,
        task_created: `New task added`,
        task_moved:  `Task moved`,
    };

    const messages_info = {
        list_deleted: `List deleted`,
        task_deleted: `Task removed`,
    };

    if(event == "user_added"){
        if(getUser == data.username){
            showToast("You were added to the board", "success")
        }
        else{
            showToast("User added", "success")
        }
    }
    else if(event == "user_deleted"){
        if(getUser == data.username){
            showToast("You were deleted from the board", "info")
            setTimeout(() => window.location.href = '/static/html/boards.html', 1500);
            return;
        }
        else{
            showToast("User deleted", "info")
        }
    }

    if (event in messages_success) showToast(messages_success[event] || "Board updated", "success");
    else if (event in messages_info) showToast(messages_info[event] || "Board updated", "info");
};

function showAddUserModal() {
    document.getElementById('add-user-input').value = '';
    document.getElementById('add-user-overlay').classList.add('open');
    document.getElementById('add-user-input').focus();
}

function closeAddUserModal() {
    document.getElementById('add-user-overlay').classList.remove('open');
}

async function confirmAddUser() {
    const username = document.getElementById('add-user-input').value.trim();
    if (!username) return;
    closeAddUserModal();
    const res = await apiFetch(`/boards/${boardId}/users`, {
        method: 'POST',
        body: JSON.stringify({ username })
    });
    if (res.ok) showToast('User added ✓', 'success');
    else if (res.status === 403) showToast('Only owner can add users', 'error');
    else showToast('Failed to add user', 'error');
};

async function showUsersModal() {
    const res = await apiFetch(`/boards/${boardId}/users`);
    const data = await res.json();
    const list = document.getElementById('users-list');

    list.innerHTML = data.users.length
        ? data.users.map(u => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--muted);">
                <span>${u} ${u === data.owner ? '👑' : ''}</span>
                ${u !== data.owner ? `<button onclick="removeUser('${u}')" style="background:none;border:none;cursor:pointer;color:#d9534f;font-size:16px;">✕</button>` : ''}
            </div>`).join('')
        : '<p style="color:var(--muted)">No users yet.</p>';

    document.getElementById('users-overlay').classList.add('open');
}

async function removeUser(username) {
    const res = await apiFetch(`/boards/${boardId}/users/${username}`, { method: 'DELETE' });
    if (res.ok) { showToast('User removed', 'info'); showUsersModal(); }
    else showToast('Failed to remove user', 'error');
}
