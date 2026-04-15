/**
 * Core Application Module
 * Shared utilities, navigation, authentication helpers, toast system.
 */

const API_BASE = 'http://localhost:5000/api';

// ─── Auth Helpers ────────────────────────────────────────────────
function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem('user'));
    } catch { return null; }
}

function authHeaders() {
    const token = getToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'index.html';
}

function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// ─── API Fetch Helper ────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: authHeaders(),
        ...options
    };

    try {
        const res = await fetch(url, config);

        if (res.status === 401) {
            logout();
            return null;
        }

        return await res.json();
    } catch (err) {
        console.warn(`API call failed: ${endpoint}`, err.message);
        return null;
    }
}

// ─── Page Navigation ─────────────────────────────────────────────
function switchPage(pageName) {
    // Hide all pages
    document.querySelectorAll('[id^="page-"]').forEach(p => p.classList.add('hidden'));

    // Show target page
    const target = document.getElementById(`page-${pageName}`);
    if (target) target.classList.remove('hidden');

    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === pageName);
    });

    // Update page title
    const titles = {
        overview: 'Overview',
        events: 'Events Log',
        analytics: 'Analytics',
        nlp: 'AI Voice Query',
        devices: 'Devices'
    };
    const titleEl = document.getElementById('pageTitle');
    if (titleEl) titleEl.textContent = titles[pageName] || pageName;

    // Load page-specific data
    if (pageName === 'events') loadEvents();
    if (pageName === 'analytics') loadAnalytics();
}

function switchAdminPage(pageName) {
    document.querySelectorAll('[id^="admin-"]').forEach(p => {
        if (p.id !== 'adminNavLink') p.classList.add('hidden');
    });
    const target = document.getElementById(`admin-${pageName}`);
    if (target) target.classList.remove('hidden');

    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === pageName);
    });
}

// ─── Sidebar Toggle ─────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// ─── Toast Notifications ─────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span> <span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ─── Format Helpers ──────────────────────────────────────────────
function formatTimestamp(isoString) {
    if (!isoString) return '—';
    try {
        const d = new Date(isoString);
        const now = new Date();
        const diff = (now - d) / 1000;

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch { return isoString; }
}

function getSeverityBadge(severity) {
    return `<span class="badge-severity ${severity}">${severity}</span>`;
}

function getEventIcon(type) {
    const icons = { drowsy: '😴', yawn: '🥱', distracted: '😵', normal: '✅' };
    const classes = { drowsy: 'drowsy', yawn: 'yawn', normal: 'normal' };
    return `<div class="event-icon ${classes[type] || 'normal'}">${icons[type] || '🔔'}</div>`;
}

// ─── Init User Info ──────────────────────────────────────────────
function initUserInfo() {
    const user = getUser();
    if (!user) return;

    const nameEl = document.getElementById('userName');
    const roleEl = document.getElementById('userRole');
    const avatarEl = document.getElementById('userAvatar');

    if (nameEl) nameEl.textContent = user.username || user.email;
    if (roleEl) roleEl.textContent = user.role || 'user';
    if (avatarEl) avatarEl.textContent = (user.username || user.email || 'U')[0].toUpperCase();

    // Show admin link if admin
    if (user.role === 'admin') {
        const adminLink = document.getElementById('adminNavLink');
        if (adminLink) adminLink.style.display = '';
    }
}

// ─── Initialize ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    initUserInfo();
});
