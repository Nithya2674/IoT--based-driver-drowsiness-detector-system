/**
 * Admin Panel Module
 * User management, API key management, and system configuration.
 */

// ─── Load Users ──────────────────────────────────────────────────
async function loadUsers() {
    const data = await apiFetch('/auth/users');
    const tbody = document.getElementById('usersTableBody');

    if (data && data.data && data.data.length > 0) {
        const users = data.data;
        document.getElementById('totalUsers').textContent = users.length;
        document.getElementById('activeUsers').textContent = users.filter(u => u.is_active).length;
        document.getElementById('adminCount').textContent = users.filter(u => u.role === 'admin').length;

        tbody.innerHTML = users.map(u => `
            <tr>
                <td><strong>${u.username || '—'}</strong></td>
                <td>${u.email}</td>
                <td><span class="badge-severity ${u.role === 'admin' ? 'critical' : 'low'}">${u.role}</span></td>
                <td><span class="text-danger" style="font-weight:600;">${u.drowsy_alerts || 0}</span></td>
                <td><span class="text-warning" style="font-weight:600;">${u.yawn_count || 0}</span></td>
                <td>${u.total_events || 0}</td>
                <td><span class="status-dot ${u.is_active !== false ? 'online' : 'offline'}"></span> ${u.recent_status || 'Active'}</td>
                <td>${u.created_at ? formatTimestamp(u.created_at) : '—'}</td>
            </tr>
        `).join('');
    } else {
        // Demo data
        document.getElementById('totalUsers').textContent = '2';
        document.getElementById('activeUsers').textContent = '2';
        document.getElementById('adminCount').textContent = '1';

        tbody.innerHTML = `
            <tr>
                <td><strong>admin</strong></td>
                <td>admin@drowsiguard.com</td>
                <td><span class="badge-severity critical">admin</span></td>
                <td><span class="text-danger" style="font-weight:600;">12</span></td>
                <td><span class="text-warning" style="font-weight:600;">2</span></td>
                <td>14</td>
                <td><span class="status-dot online"></span> Active</td>
                <td>Jan 1, 2025</td>
            </tr>
            <tr>
                <td><strong>driver01</strong></td>
                <td>driver@drowsiguard.com</td>
                <td><span class="badge-severity low">user</span></td>
                <td><span class="text-danger" style="font-weight:600;">4</span></td>
                <td><span class="text-warning" style="font-weight:600;">1</span></td>
                <td>5</td>
                <td><span class="status-dot online"></span> Active</td>
                <td>Jan 15, 2025</td>
            </tr>
        `;
    }
}

// ─── Generate API Key ────────────────────────────────────────────
function generateApiKey() {
    const key = 'dds_' + Array.from(crypto.getRandomValues(new Uint8Array(32)))
        .map(b => b.toString(16).padStart(2, '0')).join('');
    const prefix = key.substring(0, 8) + '...' + key.substring(key.length - 4);

    showToast(`New API Key generated: ${prefix}`, 'success');

    const tbody = document.getElementById('apiKeysTableBody');
    if (tbody) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>New-Device</td>
            <td><code style="color:var(--accent-primary);">${prefix}</code></td>
            <td>${new Date().toISOString().split('T')[0]}</td>
            <td><span class="badge-severity low">Active</span></td>
        `;
        tbody.appendChild(row);
    }
}

// ─── Initialize Admin ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const user = getUser();
    if (!user || user.role !== 'admin') {
        showToast('Admin access required!', 'error');
        setTimeout(() => { window.location.href = 'dashboard.html'; }, 1500);
        return;
    }

    loadUsers();
});
