/**
 * Manatrix Studio - Terminal Module
 *
 * Xterm.js terminal, WebSocket bridge, REPL mode switcher
 */

// ==========================================================================
// Terminal Init
// ==========================================================================

async function initTerminal() {
    const termEl = document.getElementById('terminal');

    await loadScript('https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js');
    await loadScript('https://cdn.jsdelivr.net/npm/@xterm/xterm-addon-fit@0.10.0/lib/xterm-addon-fit.min.js');
    await loadScript('https://cdn.jsdelivr.net/npm/@xterm/xterm-addon-web-links@0.11.0/lib/xterm-addon-web-links.min.js');

    state.terminal = new Terminal({
        cursorBlink: true, cursorStyle: 'bar', fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        theme: getTerminalTheme(state.theme), scrollback: 5000, allowTransparency: false,
    });

    const fitAddon = new FitAddon.FitAddon();
    const webLinksAddon = new WebLinksAddon.WebLinksAddon();

    state.terminal.loadAddon(fitAddon);
    state.terminal.loadAddon(webLinksAddon);
    state.terminal.open(termEl);
    fitAddon.fit();

    window.addEventListener('resize', () => fitAddon.fit());
    setTimeout(() => fitAddon.fit(), 100);

    state.terminal.onData(data => {
        if (state.replMode === 'python' && state.pyodideReady) {
            handlePyodideInput(data);
        } else if (state.replMode === 'shell') {
            handleShellInput(data);
        } else if (state.ws && state.connected) {
            state.ws.send(JSON.stringify({ type: 'data', data }));
        }
    });

    printWelcome();
}

function printWelcome() {
    if (!state.terminal) return; // Guard against init failure
    const welcome = `
  \x1b[36m  ____             ____ _                ____                          _\x1b[0m
  \x1b[36m |  _ \\  ___ _   _ / ___| |__   ___  ___|  _ \\ ___ _ __   ___  _ __ __| |\x1b[0m
  \x1b[36m | | | |/ _ \\ | | | |   | '_ \\ / _ \\/ __| |_) / _ \\ '_ \\ / _ \\| '__/ _\` |\x1b[0m
  \x1b[36m | |_| |  __/ |_| | |___| | | |  __/ (__|  _ <  __/ |_) | (_) | | | (_| |\x1b[0m
  \x1b[36m |____/ \\___|\\__, |\\____|_| |_|\\___|\\___|_| \\_\\___| .__/ \\___/|_|  \\__,_|\x1b[0m
  \x1b[36m            |___/                                |_|\x1b[0m

  \x1b[1;37m Manatrix Studio\x1b[0m - RStudio-like IDE for Manatrix CLI
  \x1b[90m Type 'help' for commands, '?' <cmd> for help\x1b[0m
  \x1b[90m Use Ctrl+Enter to run from editor, Ctrl+L to clear\x1b[0m
\x1b[90m Press Ctrl+Shift+F to search, Ctrl+\\ to split editor\x1b[0m
\x1b[90m [M] Manatrix CLI | [Py] Python (browser) | [$] Shell\x1b[0m
`;
    state.terminal.write(welcome);
    state.terminal.write('\r\n\x1b[90m$ \x1b[0m');
}

function printLine(text) {
    if (!state.terminal) return; // Guard against init failure
    state.terminal.write(text + '\r\n\x1b[90m$ \x1b[0m');
}

function clearConsole() {
    if (state.terminal) { state.terminal.clear(); printWelcome(); }
}

// ==========================================================================
// Local Input Handlers (Python & Shell REPL)
// ==========================================================================

// Input buffers for local REPL modes
let pyodideInputBuffer = '';
let shellInputBuffer = '';

function handlePyodideInput(data) {
    if (data === '\r') {
        // Enter key — execute the buffer
        state.terminal.write('\r\n');
        const code = pyodideInputBuffer.trim();
        pyodideInputBuffer = '';
        if (code) {
            runPythonCode(code);
        } else {
            state.terminal.write('\x1b[90m>>> \x1b[0m');
        }
    } else if (data === '\x7f') {
        // Backspace
        if (pyodideInputBuffer.length > 0) {
            pyodideInputBuffer = pyodideInputBuffer.slice(0, -1);
            state.terminal.write('\b \b');
        }
    } else if (data === '\x03') {
        // Ctrl+C — cancel current input
        state.terminal.write('^C\r\n\x1b[90m>>> \x1b[0m');
        pyodideInputBuffer = '';
    } else if (data === '\x0c') {
        // Ctrl+L — clear
        state.terminal.clear();
        state.terminal.write('\x1b[90m>>> \x1b[0m');
    } else if (data === '\x1b[A' || data === '\x1b[B') {
        // Up/Down arrows — history navigation (basic)
        // TODO: implement history navigation
    } else if (data === '\t') {
        // Tab — autocomplete
        const completions = window.getPyodideCompletions ? getPyodideCompletions(pyodideInputBuffer) : [];
        if (completions.length === 1) {
            const completion = completions[0];
            const suffix = completion.slice(pyodideInputBuffer.length);
            pyodideInputBuffer = completion;
            state.terminal.write(suffix);
        } else if (completions.length > 1) {
            state.terminal.write('\r\n' + completions.join('  ') + '\r\n\x1b[90m>>> \x1b[0m' + pyodideInputBuffer);
        }
    } else if (data.length === 1 && data.charCodeAt(0) >= 32) {
        // Printable character
        pyodideInputBuffer += data;
        state.terminal.write(data);
    }
}

function handleShellInput(data) {
    if (data === '\r') {
        state.terminal.write('\r\n');
        const cmd = shellInputBuffer.trim();
        shellInputBuffer = '';
        if (cmd) {
            runShellCommand(cmd).then(() => {
                state.terminal.write('\x1b[90m$ \x1b[0m');
            });
        } else {
            state.terminal.write('\x1b[90m$ \x1b[0m');
        }
    } else if (data === '\x7f') {
        if (shellInputBuffer.length > 0) {
            shellInputBuffer = shellInputBuffer.slice(0, -1);
            state.terminal.write('\b \b');
        }
    } else if (data === '\x03') {
        state.terminal.write('^C\r\n\x1b[90m$ \x1b[0m');
        shellInputBuffer = '';
    } else if (data === '\x0c') {
        state.terminal.clear();
        state.terminal.write('\x1b[90m$ \x1b[0m');
    } else if (data.length === 1 && data.charCodeAt(0) >= 32) {
        shellInputBuffer += data;
        state.terminal.write(data);
    }
}

// ==========================================================================
// WebSocket Bridge
// ==========================================================================

function initWebSocket() {
    state.reconnectAttempts = 0;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/terminal/${state.sessionId}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        state.connected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus(true);
        document.getElementById('statusSession').textContent = `Session: ${state.sessionId.slice(0, 8)}`;

        // Start heartbeat
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

        // Max reconnect guard to prevent infinite recursion
        const MAX_RECONNECTS = 20;
        if (state.reconnectAttempts >= MAX_RECONNECTS) {
            state.terminal.write('\r\n\x1b[31m[!] Max reconnection attempts reached. Please refresh the page.\x1b[0m\r\n');
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), state.maxReconnectDelay);
        state.reconnectAttempts++;
        state.terminal.write(`\r\n\x1b[33m[!] Disconnected. Reconnecting in ${Math.round(delay/1000)}s...\x1b[0m\r\n`);
        setTimeout(() => { if (!state.connected) initWebSocket(); }, delay);
    };

    state.ws.onerror = (err) => {
        state.terminal.write('\r\n\x1b[31m[!] WebSocket error\x1b[0m\r\n');
    };
}

function handleWSMessage(msg) {
    switch (msg.type) {
        case 'welcome': state.terminal.write('\r\n'); break;
        case 'output':
            state.terminal.write(highlightTerminalOutput(msg.data).replace(/\n/g, '\r\n'));
            checkForCharts(msg.data);
            break;
        case 'error':
            state.terminal.write('\r\n\x1b[31m' + msg.data.replace(/\n/g, '\r\n\x1b[31m'));
            break;
        case 'status':
            state.terminal.write('\x1b[90m[*] ' + msg.data.replace(/\n/g, '\r\n[*] ') + '\x1b[0m');
            break;
        case 'chart': addChart(msg.data); break;
        case 'done':
            state.busy = false;
            updateBusyStatus(false);
            if (msg.returncode === 0) state.terminal.write('\r\n');
            else state.terminal.write('\r\n\x1b[33m[ exited with code ' + msg.returncode + ' ]\x1b[0m\r\n');
            break;
        case 'pong': break;
        default:
            if (msg.data) state.terminal.write(msg.data.replace(/\n/g, '\r\n'));
    }
}

function sendCommand(cmd) {
    if (!state.ws || !state.connected) {
        state.terminal.write('\r\n\x1b[31m[!] Not connected\x1b[0m\r\n');
        return;
    }
    state.busy = true;
    updateBusyStatus(true);
    recordCommand(cmd);
    state.ws.send(JSON.stringify({ type: 'command', data: cmd }));
}

function checkForCharts(text) {
    const chartExts = ['.png', '.svg', '.jpg', '.jpeg'];
    for (const ext of chartExts) {
        if (text.includes(ext)) {
            const match = text.match(new RegExp(`[\\w\\-\\/]+${ext}`));
            if (match) addChart(match[0]);
        }
    }
}

// ==========================================================================
// Syntax Highlighting for Terminal Output
// ==========================================================================

function highlightTerminalOutput(text) {
    // Paths
    text = text.replace(/([A-Za-z]:\\[\w\\.-]+|\/[\w\/.-]+)/g, '\x1b[34m$1\x1b[0m');
    // URLs
    text = text.replace(/(https?:\/\/[^\s]+)/g, '\x1b[4;34m$1\x1b[0m');
    // IPs
    text = text.replace(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/g, '\x1b[36m$1\x1b[0m');
    // CVE IDs
    text = text.replace(/(CVE-\d{4}-\d+)/gi, '\x1b[35m$1\x1b[0m');
    // Hashes
    text = text.replace(/\b([a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})\b/gi, '\x1b[33m$1\x1b[0m');
    // Errors
    text = text.replace(/(\[ERROR\]|\[!\]|Error:|Exception:|Failed)/g, '\x1b[31m$1\x1b[0m');
    // Success
    text = text.replace(/(\[OK\]|\[\+\]|Success|Completed|Done)/g, '\x1b[32m$1\x1b[0m');
    // Warnings
    text = text.replace(/(\[WARNING\]|\[?\?]|Warning:|Caution:)/g, '\x1b[33m$1\x1b[0m');
    // Ports
    text = text.replace(/:([0-9]{1,5})(\s|$)/g, ':\x1b[33m$1\x1b[0m$2');
    // Numbers with units
    text = text.replace(/\b(\d+(?:\.\d+)?)(KB|MB|GB|TB|ms|s|%)\b/g, '\x1b[36m$1$2\x1b[0m');
    return text;
}

// ==========================================================================
// REPL Mode Switcher
// ==========================================================================

function initReplMode() {
    const modeLabel = document.getElementById('consoleModeLabel');
    document.querySelectorAll('.repl-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.repl-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.replMode = btn.getAttribute('data-mode');
            if (modeLabel) {
                const labels = { manatrix: 'MANATRIX', python: 'PYTHON', shell: 'SHELL' };
                modeLabel.textContent = labels[state.replMode] || 'MANATRIX';
            }
            // Handle REPL mode switch
            handleReplModeSwitch();
        });
    });
}

async function handleReplModeSwitch() {
    pyodideInputBuffer = '';
    shellInputBuffer = '';

    if (state.replMode === 'python') {
        state.terminal.write('\r\n\x1b[36m=== Python REPL Mode (Browser) ===\x1b[0m\r\n');
        state.terminal.write('\x1b[90mType Python code. Press Enter to execute.\x1b[0m\r\n');
        state.terminal.write('\x1b[90m>>> \x1b[0m');
        // Pre-load Pyodide in background for faster execution
        if (!state.pyodideReady && window.initPyodide) {
            state.terminal.write('\x1b[90m[*] Pre-loading Python runtime in background...\x1b[0m\r\n');
            initPyodide().then(() => {
                state.pyodideReady = true;
            }).catch(e => {
                state.terminal.write('\x1b[33m[!] Pyodide not available, will use server-side execution\x1b[0m\r\n');
            });
        }
    } else if (state.replMode === 'shell') {
        state.terminal.write('\r\n\x1b[36m=== Shell Mode ===\x1b[0m\r\n');
        state.terminal.write('\x1b[90mType shell commands.\x1b[0m\r\n');
        state.terminal.write('\x1b[90m$ \x1b[0m');
    } else {
        state.terminal.write('\r\n\x1b[36m=== Manatrix CLI Mode ===\x1b[0m\r\n');
        state.terminal.write('\x1b[90mType Manatrix commands.\x1b[0m\r\n');
        state.terminal.write('\x1b[90m$ \x1b[0m');
    }
}

// ==========================================================================
// Charts / Plots
// ==========================================================================

function addChart(path) {
    state.charts.push(path);

    const preview = document.getElementById('lastPlotPreview');
    const placeholder = document.getElementById('plotsPlaceholder');
    preview.src = path;
    preview.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';

    const grid = document.getElementById('plotsGrid');
    const img = document.createElement('div');
    img.style.cssText = 'background: var(--studio-bg-tertiary); border-radius: 4px; padding: 8px; text-align: center;';
    // Escape path for safe HTML attribute usage
    const safePath = escapeHtml(path);
    img.innerHTML = `<img src="${safePath}" style="max-width: 100%; max-height: 200px; border-radius: 4px; cursor: pointer;" onclick="window.open('${safePath}', '_blank')">`;
    grid.appendChild(img);

    showOutputTab('plots');
    updateStatus(`Chart saved: ${path.split('/').pop()}`);
}

function clearCharts() {
    state.charts = [];
    document.getElementById('plotsPanel').innerHTML = `
        <div style="color: var(--studio-text-muted); font-size: 11px; margin-top: 8px;" id="plotsPlaceholder">
            No plots yet<br><span style="font-size:10px;">Run 'chart' commands to see plots here</span>
        </div>
    `;
    document.getElementById('plotsGrid').innerHTML = '';
}

// ==========================================================================
// Session Recording
// ==========================================================================

// Recording functions are defined in studio-misc.js
// to avoid duplicate initialization. The studio.js bootstrap calls initRecording
// from studio-misc.js (loaded last) which assigns window.* properly.

const recorder = {
    active: false, commands: [], startTime: null,
    playbackSpeed: 1,
};

function startRecording() {
    recorder.active = true;
    recorder.commands = [];
    recorder.startTime = Date.now();
    state.terminal.write('\r\n\x1b[32m[+] Recording started\x1b[0m\r\n');
    updateStatus('Recording...');
}

function stopRecording() {
    if (!recorder.active) return;
    recorder.active = false;
    const name = prompt('Recording name:', `session_${new Date().toISOString().slice(0, 10)}`);
    if (!name) { state.terminal.write('\r\n\x1b[33m[-] Recording discarded\x1b[0m\r\n'); return; }

    fetch('/api/recording/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, commands: recorder.commands }),
    }).then(r => r.json()).then(data => {
        state.terminal.write(`\r\n\x1b[32m[+] Recording saved: ${data.id}\x1b[0m\r\n`);
    });
    updateStatus('Ready');
}

function recordCommand(cmd) {
    if (!recorder.active) return;
    recorder.commands.push({ command: cmd, timestamp: Date.now() - recorder.startTime });
}

async function listRecordings() {
    const resp = await fetch('/api/recording/list');
    const data = await resp.json();
    state.terminal.write('\r\n\x1b[36m=== Session Recordings ===\x1b[0m\r\n');
    data.recordings.forEach(r => {
        state.terminal.write(`  ${r.id}  ${r.name}  (${r.commands} cmds, ${Math.round(r.duration/1000)}s)\r\n`);
    });
    state.terminal.write('\x1b[90mUse playRecording("id") to replay\x1b[0m\r\n');
}

async function playRecording(id) {
    const resp = await fetch(`/api/recording/load/${id}`);
    const data = await resp.json();
    if (!data.success) { state.terminal.write('\r\n\x1b[31m[-] Recording not found\x1b[0m\r\n'); return; }

    const recording = data.recording;
    state.terminal.write(`\r\n\x1b[36m[*] Playing: ${recording.name} (${recording.commands.length} commands)\x1b[0m\r\n`);
    state.terminal.write('\x1b[90mPress Esc to stop\x1b[0m\r\n');

    let cancelled = false;
    const cancelHandler = () => { cancelled = true; };
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') { cancelled = true; document.removeEventListener('keydown', escHandler); }
    });

    for (let i = 0; i < recording.commands.length && !cancelled; i++) {
        const cmd = recording.commands[i];
        const delay = i > 0 ? (recording.commands[i].timestamp - recording.commands[i-1].timestamp) : 0;
        await new Promise(r => setTimeout(r, Math.min(delay / recorder.playbackSpeed, 3000)));
        if (cancelled) break;
        state.terminal.write(`\r\n\x1b[90m> \x1b[0m${cmd.command}\r\n`);
        sendCommand(cmd.command);
        await new Promise(r => setTimeout(r, 500));
    }
    state.terminal.write(cancelled ? '\r\n\x1b[33m[-] Playback stopped\x1b[0m\r\n' : '\r\n\x1b[32m[+] Playback complete\x1b[0m\r\n');
}
