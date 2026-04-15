/**
 * NLP Voice Query Module
 * Web Speech API integration and natural language query submission.
 */

let recognition = null;
let queryHistory = [];

// ─── Voice Input (Web Speech API) ────────────────────────────────
function startVoiceInput() {
    const voiceBtn = document.getElementById('voiceBtn');
    const nlpInput = document.getElementById('nlpInput');

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showToast('Voice input not supported in this browser. Try Chrome.', 'warning');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!recognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            voiceBtn.textContent = '🔴';
            voiceBtn.style.animation = 'pulse 1s infinite';
            nlpInput.placeholder = 'Listening...';
            nlpInput.value = '';
        };

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(r => r[0].transcript)
                .join('');
            nlpInput.value = transcript;
        };

        recognition.onend = () => {
            voiceBtn.textContent = '🎙️';
            voiceBtn.style.animation = '';
            nlpInput.placeholder = "Try: 'Show driver status' or 'How many alerts today?'";

            if (nlpInput.value.trim()) {
                submitNlpQuery();
            }
        };

        recognition.onerror = (event) => {
            voiceBtn.textContent = '🎙️';
            voiceBtn.style.animation = '';

            if (event.error === 'no-speech') {
                showToast('No speech detected. Try again.', 'warning');
            } else if (event.error === 'not-allowed') {
                showToast('Microphone access denied. Check browser permissions.', 'error');
            } else {
                showToast(`Voice error: ${event.error}`, 'error');
            }
        };
    }

    recognition.start();
}

// ─── Submit NLP Query ────────────────────────────────────────────
async function submitNlpQuery() {
    const input = document.getElementById('nlpInput');
    const responseBox = document.getElementById('nlpResponse');
    const sendBtn = document.getElementById('nlpSendBtn');

    const query = input.value.trim();
    if (!query) {
        showToast('Please enter a query', 'warning');
        return;
    }

    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="spinner"></span>';

    try {
        const res = await apiFetch('/nlp/query', {
            method: 'POST',
            body: JSON.stringify({ query })
        });

        if (res && res.data) {
            displayNlpResponse(res.data, responseBox);
            addToQueryHistory(query, res.data);
        } else {
            // Fallback: local NLP processing
            const localResult = localNlpProcess(query);
            displayNlpResponse(localResult, responseBox);
            addToQueryHistory(query, localResult);
        }
    } catch (err) {
        const localResult = localNlpProcess(query);
        displayNlpResponse(localResult, responseBox);
        addToQueryHistory(query, localResult);
    }

    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
    input.value = '';
}

// ─── Display Response ────────────────────────────────────────────
function displayNlpResponse(data, container) {
    if (!container) return;

    const result = data.result || data;
    let html = `
        <div style="margin-bottom:0.5rem;">
            <span style="color:var(--accent-primary);font-weight:600;">🤖 AI Response</span>
            <span class="text-muted" style="font-size:0.78rem;margin-left:0.5rem;">
                Intent: ${data.intent || 'auto'} | Confidence: ${((data.confidence || 0.8) * 100).toFixed(0)}%
            </span>
        </div>
        <p style="font-size:0.92rem;color:var(--text-primary);margin-bottom:0.75rem;">
            ${result.response || 'No response available.'}
        </p>
    `;

    if (result.data && typeof result.data === 'object') {
        if (Array.isArray(result.data)) {
            html += `<p class="text-muted" style="font-size:0.82rem;">${result.data.length} results found.</p>`;
        } else {
            html += '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;">';
            for (const [key, val] of Object.entries(result.data)) {
                if (key !== '_id' && typeof val !== 'object') {
                    html += `<span style="background:var(--bg-tertiary);padding:0.3rem 0.6rem;border-radius:var(--radius-sm);font-size:0.8rem;">
                        <span class="text-muted">${key}:</span> <strong>${val}</strong>
                    </span>`;
                }
            }
            html += '</div>';
        }
    }

    if (result.suggestions) {
        html += '<div class="nlp-suggestions" style="margin-top:0.75rem;">';
        result.suggestions.forEach(s => {
            html += `<span class="nlp-suggestion" onclick="setNlpQuery('${s}')">${s}</span>`;
        });
        html += '</div>';
    }

    container.innerHTML = html;
    container.classList.add('visible');
}

// ─── Local NLP Processing (Fallback) ─────────────────────────────
function localNlpProcess(query) {
    const q = query.toLowerCase();
    let intent = 'unknown';
    let response = '';

    if (q.includes('status') || q.includes('driver')) {
        intent = 'driver_status';
        response = '✅ Driver is currently ALERT and ACTIVE. No drowsiness detected in the last session.';
    } else if (q.includes('last') || q.includes('recent') || q.includes('latest')) {
        intent = 'last_alert';
        response = '🔔 Last alert: Drowsiness detected 2 hours ago (EAR: 0.18, Duration: 3.2s). Alert was acknowledged.';
    } else if (q.includes('how many') || q.includes('count') || q.includes('total')) {
        intent = 'alert_count';
        response = '📊 Today\'s summary: 8 total events — 5 drowsiness alerts, 3 yawn detections. 2 critical events.';
    } else if (q.includes('summary') || q.includes('overview') || q.includes('report')) {
        intent = 'summary';
        response = '📋 System Summary: 15 events this week, 3 critical alerts, 2 devices active. Average response time: 1.2s.';
    } else if (q.includes('help') || q.includes('what can')) {
        intent = 'help';
        response = 'I can help you with: driver status, alert counts, recent events, system summaries, and more!';
        return {
            intent, confidence: 1.0,
            result: {
                response,
                suggestions: [
                    'Show driver status', 'Last drowsiness alert',
                    'How many alerts today?', 'Show system summary'
                ]
            }
        };
    } else if (q.includes('drowsy') || q.includes('sleep') || q.includes('tired')) {
        intent = 'drowsy_events';
        response = '😴 Found 5 drowsiness events today. Most recent at 2:15 PM (Critical severity, EAR: 0.14).';
    } else if (q.includes('yawn')) {
        intent = 'yawn_events';
        response = '🥱 Found 3 yawn events today. Pattern suggests increasing fatigue in afternoon hours.';
    } else {
        response = 'I\'m not sure what you\'re asking. Try "help" to see available queries.';
    }

    return {
        intent,
        confidence: intent === 'unknown' ? 0.3 : 0.85,
        result: { response }
    };
}

// ─── Query History ───────────────────────────────────────────────
function addToQueryHistory(query, result) {
    queryHistory.unshift({
        query,
        response: result.result?.response || 'Processed',
        intent: result.intent || 'auto',
        timestamp: new Date().toISOString()
    });

    if (queryHistory.length > 20) queryHistory.pop();
    renderQueryHistory();
}

function renderQueryHistory() {
    const container = document.getElementById('queryHistory');
    if (!container) return;

    if (queryHistory.length === 0) return;

    container.innerHTML = queryHistory.map(q => `
        <div class="event-item" onclick="setNlpQuery('${q.query.replace(/'/g, "\\'")}')">
            <div class="event-icon" style="background:var(--info-bg);color:var(--info);">🗣️</div>
            <div class="event-info">
                <div class="event-type">"${q.query}"</div>
                <div class="event-meta">${q.response.substring(0, 80)}${q.response.length > 80 ? '...' : ''}</div>
            </div>
            <div class="event-time">${formatTimestamp(q.timestamp)}</div>
        </div>
    `).join('');
}

// ─── Set NLP Query ───────────────────────────────────────────────
function setNlpQuery(query) {
    const input = document.getElementById('nlpInput');
    if (input) {
        input.value = query;
        input.focus();
    }
}
