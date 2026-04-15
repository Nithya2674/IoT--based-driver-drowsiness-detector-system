/**
 * Authentication Module
 * Handles login, registration, tab switching, and JWT token management.
 */

const API_BASE = 'http://localhost:5000/api';

// ─── Tab Switching ───────────────────────────────────────────────
function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const loginTab = document.getElementById('loginTab');
    const registerTab = document.getElementById('registerTab');
    const msg = document.getElementById('authMessage');

    msg.textContent = '';

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
    }
}

// ─── Login Handler ───────────────────────────────────────────────
async function handleLogin(event) {
    event.preventDefault();
    const btn = document.getElementById('loginBtn');
    const msg = document.getElementById('authMessage');

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!email || !password) {
        msg.innerHTML = '<span style="color:var(--danger);">Please fill all fields</span>';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Signing in...';

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.ok && data.data) {
            // Save token and user info
            localStorage.setItem('token', data.data.access_token);
            localStorage.setItem('user', JSON.stringify(data.data.user));

            msg.innerHTML = '<span style="color:var(--success);">✅ Login successful! Redirecting...</span>';

            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 800);
        } else {
            msg.innerHTML = `<span style="color:var(--danger);">❌ ${data.message || 'Login failed'}</span>`;
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    } catch (err) {
        // Fallback: demo mode without backend
        if (email === 'admin@drowsiguard.com' && password === 'admin123') {
            const demoUser = {
                username: 'admin',
                email: 'admin@drowsiguard.com',
                role: 'admin',
                _id: 'demo_admin'
            };
            localStorage.setItem('token', 'demo-token-' + Date.now());
            localStorage.setItem('user', JSON.stringify(demoUser));
            msg.innerHTML = '<span style="color:var(--success);">✅ Demo login! Redirecting...</span>';
            setTimeout(() => { window.location.href = 'dashboard.html'; }, 800);
        } else {
            msg.innerHTML = '<span style="color:var(--warning);">⚠️ Backend offline. Use demo: admin@drowsiguard.com / admin123</span>';
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    }
}

// ─── Register Handler ────────────────────────────────────────────
async function handleRegister(event) {
    event.preventDefault();
    const btn = document.getElementById('registerBtn');
    const msg = document.getElementById('authMessage');

    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    const role = document.getElementById('regRole').value;

    if (!username || !email || !password) {
        msg.innerHTML = '<span style="color:var(--danger);">Please fill all fields</span>';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating account...';

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, role })
        });

        const data = await res.json();

        if (res.ok && data.data) {
            localStorage.setItem('token', data.data.access_token);
            localStorage.setItem('user', JSON.stringify(data.data.user));

            msg.innerHTML = '<span style="color:var(--success);">✅ Account created! Redirecting...</span>';
            setTimeout(() => { window.location.href = 'dashboard.html'; }, 800);
        } else {
            msg.innerHTML = `<span style="color:var(--danger);">❌ ${data.message || 'Registration failed'}</span>`;
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
    } catch (err) {
        // Fallback demo mode
        const demoUser = { username, email, role, _id: 'demo_' + Date.now() };
        localStorage.setItem('token', 'demo-token-' + Date.now());
        localStorage.setItem('user', JSON.stringify(demoUser));
        msg.innerHTML = '<span style="color:var(--success);">✅ Demo account created! Redirecting...</span>';
        setTimeout(() => { window.location.href = 'dashboard.html'; }, 800);
    }
}

// ─── Check Existing Session ──────────────────────────────────────
(function checkSession() {
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = 'dashboard.html';
    }
})();
