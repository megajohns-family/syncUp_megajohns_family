function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'flex';
    setTimeout(() => { toast.style.display = 'none'; }, 3500);
}

async function doRegister(e) {
    e.preventDefault();
    const login = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    const res = await fetch('/users/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login, password })
    });

    if (res.ok) {
        showToast('Account created successfully!', 'success');


        const loginRes = await fetch('/users/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password })
        });
        const data = await loginRes.json();
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', login);

        setTimeout(() => window.location.href = '/static/html/index.html', 1000);
    } else {
        showToast('Username already taken or invalid', 'error');
    }
}
if (localStorage.getItem('token')) {
    window.location.href = '/static/html/index.html';
}