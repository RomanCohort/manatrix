/**
 * Manatrix Studio - Misc Module
 *
 * Tutorial, wordlist analyzer, enhanced WebSocket, recording init
 */

// ==========================================================================
// Interactive Tutorial
// ==========================================================================

const tutorialSteps = [
    { target: '#editorPanel', title: 'Source Editor', content: 'Edit your Python scripts here. Press Ctrl+Enter to run code.' },
    { target: '#consolePanel', title: 'Terminal', content: 'Execute Manatrix CLI commands, Python, or Shell scripts.' },
    { target: '#leftSidebar', title: 'File Browser', content: 'Navigate your workspace and open files.' },
    { target: '#rightSidebar', title: 'Environment', content: 'View variables, history, and generated plots.' },
    { target: '#replSwitcher', title: 'REPL Modes', content: 'Switch between Manatrix CLI (M), Python (Py), and Shell ($).' },
    { target: '#themeBtn', title: 'Themes', content: 'Click to change the UI theme (Dark, Light, Matrix, Nord, Solarized).' },
    { target: '#gitSection', title: 'Git Panel', content: 'View git status, commit, push, and pull changes.' },
    { target: '', title: 'Welcome!', content: 'You are ready to use Manatrix Studio! Press Skip to close this tutorial.' },
];

function initTutorial() {
    if (!localStorage.getItem('studio_tutorial_done')) {
        setTimeout(startTutorial, 3000);
    }
}

function startTutorial() {
    let current = 0;
    let overlay = null;
    let tooltip = null;

    function cleanup() {
        if (overlay) { overlay.remove(); overlay = null; }
        if (tooltip) { tooltip.remove(); tooltip = null; }
        // Remove outline from previous target
        document.querySelectorAll('.tutorial-highlight').forEach(el => {
            el.style.outline = '';
            el.classList.remove('tutorial-highlight');
        });
    }

    function showStep() {
        cleanup();

        if (current >= tutorialSteps.length) {
            localStorage.setItem('studio_tutorial_done', 'true');
            return;
        }

        const step = tutorialSteps[current];
        const target = document.querySelector(step.target);

        overlay = document.createElement('div');
        overlay.className = 'tutorial-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9998;pointer-events:none;';
        document.body.appendChild(overlay);

        tooltip = document.createElement('div');
        tooltip.className = 'tutorial-tooltip';
        tooltip.innerHTML = `
            <div style="font-weight:600;margin-bottom:8px;">${escapeHtml(step.title)}</div>
            <div style="font-size:12px;margin-bottom:12px;">${escapeHtml(step.content)}</div>
            <div style="display:flex;gap:8px;justify-content:flex-end;">
                <button class="tutorial-skip">Skip</button>
                <button class="tutorial-next">${current === tutorialSteps.length - 1 ? 'Finish' : 'Next'}</button>
            </div>
        `;

        if (target) {
            const rect = target.getBoundingClientRect();
            tooltip.style.cssText = `position:fixed;left:${Math.min(rect.right + 10, window.innerWidth - 270)}px;top:${Math.max(rect.top, 10)}px;width:250px;background:var(--studio-bg-secondary);border:1px solid var(--studio-accent-primary);border-radius:8px;padding:16px;z-index:9999;pointer-events:auto;`;
            target.style.outline = '2px solid var(--studio-accent-primary)';
            target.classList.add('tutorial-highlight');
        } else {
            tooltip.style.cssText = 'position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:250px;background:var(--studio-bg-secondary);border:1px solid var(--studio-accent-primary);border-radius:8px;padding:16px;z-index:9999;pointer-events:auto;';
        }

        document.body.appendChild(tooltip);

        tooltip.querySelector('.tutorial-skip').onclick = () => {
            cleanup();
            localStorage.setItem('studio_tutorial_done', 'true');
        };

        tooltip.querySelector('.tutorial-next').onclick = () => {
            current++;
            showStep();
        };

        // Click overlay to close
        overlay.onclick = () => {
            cleanup();
            localStorage.setItem('studio_tutorial_done', 'true');
        };
    }

    showStep();
}

// ==========================================================================
// Wordlist Analyzer
// ==========================================================================

async function analyzeWordlist(path) {
    state.terminal.write(`\r\n\x1b[36m[*] Analyzing wordlist: ${path}\x1b[0m\r\n`);

    const resp = await fetch('/api/wordlist/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
    });

    const data = await resp.json();

    if (!data.success) {
        state.terminal.write(`\x1b[31m[-] Error: ${data.error}\x1b[0m\r\n`);
        return;
    }

    state.terminal.write(`\r\n\x1b[32m=== Wordlist Analysis ===\x1b[0m\r\n`);
    state.terminal.write(`  Total entries: \x1b[36m${data.total_entries.toLocaleString()}\x1b[0m\r\n`);
    state.terminal.write(`  File size: \x1b[36m${(data.file_size / 1024 / 1024).toFixed(2)} MB\x1b[0m\r\n`);
    state.terminal.write(`  Length range: \x1b[36m${data.length_stats.min} - ${data.length_stats.max}\x1b[0m (avg: ${data.length_stats.average})\r\n`);
    state.terminal.write(`  Entropy score: \x1b[36m${data.entropy_score}%\x1b[0m (Quality: ${data.quality_rating})\r\n`);
    state.terminal.write(`\r\n  Charset coverage:\r\n`);
    state.terminal.write(`    Upper: ${data.charset_coverage.percentages.upper}%\r\n`);
    state.terminal.write(`    Lower: ${data.charset_coverage.percentages.lower}%\r\n`);
    state.terminal.write(`    Digits: ${data.charset_coverage.percentages.digit}%\r\n`);
    state.terminal.write(`    Special: ${data.charset_coverage.percentages.special}%\r\n`);
}

function showWordlistAnalyzer() {
    const path = prompt('Wordlist file path:');
    if (path) analyzeWordlist(path);
}

// ==========================================================================
// Enhanced WebSocket
// ==========================================================================

function initEnhancedWebSocket() {
    state.reconnectAttempts = 0;
    state.maxReconnectDelay = 30000;
    state.heartbeatInterval = null;
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/terminal/${state.sessionId}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        state.connected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus(true);

        if (state.heartbeatInterval) clearInterval(state.heartbeatInterval);
        state.heartbeatInterval = setInterval(() => {
            if (state.ws && state.connected) state.ws.send(JSON.stringify({ type: 'ping' }));
        }, 30000);
    };

    state.ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWSMessage(msg);
        } catch(e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    };

    state.ws.onclose = () => {
        state.connected = false;
        updateConnectionStatus(false);
        if (state.heartbeatInterval) { clearInterval(state.heartbeatInterval); state.heartbeatInterval = null; }

        const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), state.maxReconnectDelay);
        state.reconnectAttempts++;

        state.terminal.write(`\r\n\x1b[33m[!] Disconnected. Reconnecting in ${Math.round(delay/1000)}s...\x1b[0m\r\n`);
        setTimeout(() => { if (!state.connected) connectWebSocket(); }, delay);
    };

    state.ws.onerror = () => {
        state.terminal.write('\r\n\x1b[31m[!] WebSocket error\x1b[0m\r\n');
    };
}

// Override initWebSocket
const originalInitWebSocket = initWebSocket;
function initWebSocket() {
    initEnhancedWebSocket();
    connectWebSocket();
}

// ==========================================================================
// Recording Init
// ==========================================================================

function initRecording() {
    window.startRecording = startRecording;
    window.stopRecording = stopRecording;
    window.playRecording = playRecording;
    window.listRecordings = listRecordings;
}