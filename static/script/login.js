function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'flex';
    setTimeout(() => { toast.style.display = 'none'; }, 3500);
}

async function doLogin(e) {
    e.preventDefault();
    const login = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    const res = await fetch('/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login, password })
    });

    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', login);
        showToast('Welcome back!', 'success');
        setTimeout(() => window.location.href = '/static/html/index.html', 800);
    } else {
        showToast('Invalid username or password', 'error');
    }
}
if (localStorage.getItem('token')) {
    window.location.href = '/static/html/index.html';
}