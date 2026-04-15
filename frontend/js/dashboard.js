/**
 * Dashboard Module
 * Charts, stats, event feed, and real-time data polling.
 */

let trendChart = null;
let distributionChart = null;
let hourlyChart = null;
let severityChart = null;
let currentPage = 1;
let refreshInterval = null;

// ─── Demo Data Generator ────────────────────────────────────────
function generateDemoData() {
    const types = ['drowsy', 'yawn', 'drowsy', 'yawn', 'drowsy'];
    const severities = ['critical', 'high', 'medium', 'low', 'medium'];
    const events = [];

    for (let i = 0; i < 15; i++) {
        const hoursAgo = Math.floor(Math.random() * 168);
        const d = new Date(Date.now() - hoursAgo * 3600000);
        events.push({
            _id: `demo_${i}`,
            event_type: types[i % types.length],
            severity: severities[i % severities.length],
            ear_value: (Math.random() * 0.15 + 0.1).toFixed(3),
            mar_value: (Math.random() * 0.5 + 0.5).toFixed(3),
            device_id: i % 3 === 0 ? 'ESP32-CAM-001' : 'RPi-CAM-001',
            driver_name: i % 2 === 0 ? 'John Driver' : 'Admin Demo',
            timestamp: d.toISOString(),
            acknowledged: i > 10
        });
    }

    events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    return events;
}

// ─── Load Dashboard Summary ─────────────────────────────────────
async function loadDashboardSummary() {
    const data = await apiFetch('/dashboard/summary');

    if (data && data.data) {
        const s = data.data;
        document.getElementById('statTotalEvents').textContent = s.today.total_events;
        document.getElementById('statDrowsy').textContent = s.today.drowsy_events;
        document.getElementById('statYawns').textContent = s.today.yawn_events;

        const status = s.today.critical_events > 0 ? 'Drowsy ⚠️' : 'Active';
        document.getElementById('statStatus').textContent = status;

        if (s.recent_events && s.recent_events.length > 0) {
            renderEventFeed(s.recent_events, 'recentEventFeed');
        }

        document.getElementById('eventBadge').textContent = s.today.total_events;
    } else {
        loadDemoSummary();
    }
}

function loadDemoSummary() {
    const events = generateDemoData();
    const todayEvents = events.filter(e => {
        const d = new Date(e.timestamp);
        const now = new Date();
        return d.toDateString() === now.toDateString();
    });

    document.getElementById('statTotalEvents').textContent = events.length;
    document.getElementById('statDrowsy').textContent = events.filter(e => e.event_type === 'drowsy').length;
    document.getElementById('statYawns').textContent = events.filter(e => e.event_type === 'yawn').length;
    document.getElementById('statStatus').textContent = 'Active';
    document.getElementById('eventBadge').textContent = events.length;

    renderEventFeed(events.slice(0, 8), 'recentEventFeed');
    window._demoEvents = events;
}

// ─── Render Event Feed ───────────────────────────────────────────
function renderEventFeed(events, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔔</div>
                <h3>No events yet</h3>
                <p>Events will appear here when drowsiness is detected.</p>
            </div>`;
        return;
    }

    container.innerHTML = events.map(e => `
        <div class="event-item" onclick="showToast('Event: ${e.event_type} at ${formatTimestamp(e.timestamp)}','info')">
            ${getEventIcon(e.event_type)}
            <div class="event-info">
                <div class="event-type">${e.event_type} Detection</div>
                <div class="event-meta">Driver: <b>${e.driver_name || e.driver_id || 'Unknown'}</b> | EAR: ${e.ear_value} | MAR: ${e.mar_value}</div>
            </div>
            ${getSeverityBadge(e.severity || 'medium')}
            <div class="event-time">${formatTimestamp(e.timestamp)}</div>
        </div>
    `).join('');
}

// ─── Load Events Table ───────────────────────────────────────────
async function loadEvents() {
    const type = document.getElementById('filterType')?.value || '';
    const severity = document.getElementById('filterSeverity')?.value || '';

    let params = `?page=${currentPage}&per_page=15`;
    if (type) params += `&type=${type}`;
    if (severity) params += `&severity=${severity}`;

    const data = await apiFetch(`/events${params}`);
    const tbody = document.getElementById('eventsTableBody');

    if (data && data.data && data.data.length > 0) {
        renderEventsTable(data.data, tbody);
        document.getElementById('eventCount').textContent = `${data.pagination?.total || data.data.length} events`;
    } else {
        const events = (window._demoEvents || generateDemoData());
        let filtered = events;
        if (type) filtered = filtered.filter(e => e.event_type === type);
        if (severity) filtered = filtered.filter(e => e.severity === severity);
        renderEventsTable(filtered, tbody);
        document.getElementById('eventCount').textContent = `${filtered.length} events (demo)`;
    }
}

function renderEventsTable(events, tbody) {
    if (!tbody) return;

    if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No events found</td></tr>';
        return;
    }

    tbody.innerHTML = events.map(e => `
        <tr>
            <td>
                <div class="flex items-center gap-1">
                    ${getEventIcon(e.event_type)}
                    <span style="text-transform:capitalize;font-weight:500;">${e.event_type}</span>
                </div>
            </td>
            <td>${getSeverityBadge(e.severity || 'medium')}</td>
            <td>${e.ear_value}</td>
            <td>${e.mar_value}</td>
            <td><strong>${e.driver_name || e.driver_id || 'Unknown'}</strong></td>
            <td>${e.device_id || 'default'}</td>
            <td>${formatTimestamp(e.timestamp)}</td>
            <td>${e.acknowledged ? '<span style="color:var(--success);">✓</span>' : '<span style="color:var(--text-muted);">—</span>'}</td>
        </tr>
    `).join('');
}

function changePage(delta) {
    currentPage = Math.max(1, currentPage + delta);
    loadEvents();
}

// ─── Charts ──────────────────────────────────────────────────────
function initCharts() {
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } }
        },
        scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        }
    };

    // Trend Chart
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        const labels = [];
        const drowsyData = [];
        const yawnData = [];
        for (let i = 6; i >= 0; i--) {
            const d = new Date(Date.now() - i * 86400000);
            labels.push(d.toLocaleDateString('en-US', { weekday: 'short' }));
            drowsyData.push(Math.floor(Math.random() * 8) + 1);
            yawnData.push(Math.floor(Math.random() * 6) + 1);
        }

        trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Drowsy Alerts',
                        data: drowsyData,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239,68,68,0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Yawn Events',
                        data: yawnData,
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245,158,11,0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: chartDefaults
        });
    }

    // Distribution Chart
    const distCtx = document.getElementById('distributionChart');
    if (distCtx) {
        distributionChart = new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: ['Drowsy', 'Yawn', 'Normal'],
                datasets: [{
                    data: [35, 25, 40],
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderColor: '#1a2035',
                    borderWidth: 3,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', padding: 20, font: { family: 'Inter' } }
                    }
                }
            }
        });
    }
}

function updateCharts() {
    // Update with new data from API or regenerate demo
    if (trendChart) {
        const newDrowsy = [];
        const newYawn = [];
        for (let i = 0; i < 7; i++) {
            newDrowsy.push(Math.floor(Math.random() * 8) + 1);
            newYawn.push(Math.floor(Math.random() * 6) + 1);
        }
        trendChart.data.datasets[0].data = newDrowsy;
        trendChart.data.datasets[1].data = newYawn;
        trendChart.update();
    }
}

// ─── Analytics Page ──────────────────────────────────────────────
function loadAnalytics() {
    // Hourly Chart
    const hourlyCtx = document.getElementById('hourlyChart');
    if (hourlyCtx && !hourlyChart) {
        const hourLabels = Array.from({length: 24}, (_, i) => `${i}:00`);
        const hourData = Array.from({length: 24}, () => Math.floor(Math.random() * 5));
        // Peak hours for drowsiness
        hourData[2] = 8; hourData[3] = 10; hourData[14] = 7; hourData[15] = 6;

        hourlyChart = new Chart(hourlyCtx, {
            type: 'bar',
            data: {
                labels: hourLabels,
                datasets: [{
                    label: 'Events per Hour',
                    data: hourData,
                    backgroundColor: 'rgba(99,102,241,0.6)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: {
                    x: { ticks: { color: '#64748b', maxRotation: 45 }, grid: { display: false } },
                    y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    // Severity Chart
    const sevCtx = document.getElementById('severityChart');
    if (sevCtx && !severityChart) {
        severityChart = new Chart(sevCtx, {
            type: 'polarArea',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [5, 12, 25, 18],
                    backgroundColor: [
                        'rgba(239,68,68,0.7)', 'rgba(249,115,22,0.7)',
                        'rgba(245,158,11,0.7)', 'rgba(16,185,129,0.7)'
                    ],
                    borderColor: '#1a2035',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: 'Inter' } }
                    }
                },
                scales: { r: { ticks: { display: false }, grid: { color: 'rgba(255,255,255,0.05)' } } }
            }
        });
    }

    // Session stats
    const statsEl = document.getElementById('sessionStats');
    if (statsEl) {
        statsEl.innerHTML = `
            <div class="stats-grid" style="margin-bottom:0;">
                <div class="stat-card"><div class="stat-value">24.3</div><div class="stat-label">Avg Blinks/min</div></div>
                <div class="stat-card"><div class="stat-value">2.1s</div><div class="stat-label">Avg Eye Closure</div></div>
                <div class="stat-card"><div class="stat-value">15</div><div class="stat-label">Sessions Logged</div></div>
                <div class="stat-card"><div class="stat-value">87%</div><div class="stat-label">Alert Rate</div></div>
            </div>
        `;
    }
}

// ─── Refresh Dashboard ───────────────────────────────────────────
async function refreshDashboard() {
    showToast('Refreshing dashboard...', 'info');
    await loadDashboardSummary();
    updateCharts();
    showToast('Dashboard updated!', 'success');
}

// ─── Auto-refresh ────────────────────────────────────────────────
function startAutoRefresh() {
    refreshInterval = setInterval(async () => {
        await loadDashboardSummary();
    }, 30000); // Every 30 seconds
}

// ─── Initialize Dashboard ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardSummary();
    initCharts();
    startAutoRefresh();
});
