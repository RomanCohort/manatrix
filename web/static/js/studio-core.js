/**
 * Manatrix Studio - Core State & Utilities
 *
 * Shared state object, theme management, connection status, helpers
 */

// ==========================================================================
// Global Studio Object
// ==========================================================================

window.Studio = window.Studio || {};

// ==========================================================================
// State
// ==========================================================================

const state = {
    sessionId: (() => {
        const saved = localStorage.getItem('studio_session_id');
        if (saved) return saved;
        const id = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
        localStorage.setItem('studio_session_id', id);
        return id;
    })(),
    ws: null,
    connected: false,
    terminal: null,
    editor: null,
    editorTabs: [],
    activeTab: null,
    currentPath: '.',
    historyIndex: -1,
    commandHistory: [],
    charts: [],
    theme: localStorage.getItem('studio_theme') || 'dark',
    busy: false,
    saveTimer: null,
    replMode: 'manatrix',
    splitMode: 'none',
    editor2: null,
    activeTab2: null,
    editorTabs2: [],
    reconnectAttempts: 0,
    maxReconnectDelay: 30000,
    heartbeatInterval: null,
    pyodideReady: false,
    pyodideNamespace: {},
};

// Regex escape helper
const re = { escape: s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') };

// ==========================================================================
// Theme
// ==========================================================================

function initTheme() {
    const stored = localStorage.getItem('studio_theme') || 'dark';
    setTheme(stored);
    document.getElementById('themeBtn').addEventListener('click', showThemeMenu);
}

function setTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('studio_theme', theme);
    if (state.terminal) {
        state.terminal.options.theme = getTerminalTheme(theme);
    }
}

function showThemeMenu() {
    const existing = document.getElementById('themeMenu');
    if (existing) { existing.remove(); return; }

    fetch('/api/themes').then(r => r.json()).then(data => {
        const menu = document.createElement('div');
        menu.id = 'themeMenu';
        menu.style.cssText = 'position:fixed;top:36px;right:60px;background:var(--studio-bg-secondary);border:1px solid var(--studio-border);border-radius:6px;z-index:9999;min-width:180px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.4);';

        data.themes.forEach(t => {
            const item = document.createElement('div');
            item.style.cssText = 'display:flex;align-items:center;gap:10px;padding:8px 14px;cursor:pointer;';
            item.innerHTML = `
                <span style="width:16px;height:16px;border-radius:50%;background:${t.preview.bg};border:2px solid ${t.preview.accent};flex-shrink:0;"></span>
                <span style="flex:1;font-size:12px;">${escapeHtml(t.name)}</span>
                ${state.theme === t.id ? '<span style="color:var(--studio-accent-primary);font-size:11px;">&#x2713;</span>' : ''}
            `;
            item.addEventListener('click', () => { setTheme(t.id); menu.remove(); });
            item.addEventListener('mouseenter', () => item.style.background = 'var(--studio-bg-hover)');
            item.addEventListener('mouseleave', () => item.style.background = '');
            menu.appendChild(item);
        });

        document.body.appendChild(menu);
        setTimeout(() => {
            document.addEventListener('click', function handler(e) {
                if (!menu.contains(e.target) && e.target.id !== 'themeBtn') {
                    menu.remove(); document.removeEventListener('click', handler);
                }
            });
        }, 50);
    });
}

function toggleTheme() {
    const themes = ['dark', 'light', 'matrix', 'nord', 'solarized'];
    const idx = themes.indexOf(state.theme);
    setTheme(themes[(idx + 1) % themes.length]);
}

function getTerminalTheme(theme) {
    const themes = {
        dark: { background: '#0c0c0c', foreground: '#cccccc', cursor: '#cccccc', cursorAccent: '#0c0c0c', selection: 'rgba(52, 152, 219, 0.4)', black: '#000000', red: '#e74c3c', green: '#2ecc71', yellow: '#f39c12', blue: '#3498db', magenta: '#9b59b6', cyan: '#1abc9c', white: '#cccccc', brightBlack: '#666666', brightRed: '#e74c3c', brightGreen: '#2ecc71', brightYellow: '#f39c12', brightBlue: '#3498db', brightMagenta: '#9b59b6', brightCyan: '#1abc9c', brightWhite: '#ffffff' },
        light: { background: '#ffffff', foreground: '#333333', cursor: '#333333', cursorAccent: '#ffffff', selection: 'rgba(52, 152, 219, 0.3)', black: '#000000', red: '#cc0000', green: '#009900', yellow: '#999900', blue: '#0066cc', magenta: '#993366', cyan: '#008080', white: '#cccccc', brightBlack: '#666666', brightRed: '#cc0000', brightGreen: '#009900', brightYellow: '#b3b300', brightBlue: '#0066cc', brightMagenta: '#cc6699', brightCyan: '#009980', brightWhite: '#ffffff' },
        matrix: { background: '#0d0d0d', foreground: '#00ff00', cursor: '#00ff00', selection: 'rgba(0, 255, 0, 0.3)', black: '#000000', red: '#ff0000', green: '#00ff00', yellow: '#ffff00', blue: '#0000ff', magenta: '#ff00ff', cyan: '#00ffff', white: '#cccccc', brightBlack: '#666666', brightRed: '#ff4444', brightGreen: '#88ff88', brightYellow: '#ffff88', brightBlue: '#8888ff', brightMagenta: '#ff88ff', brightCyan: '#88ffff', brightWhite: '#ffffff' },
        nord: { background: '#2e3440', foreground: '#eceff4', cursor: '#88c0d0', selection: 'rgba(136, 192, 208, 0.3)', black: '#3b4252', red: '#bf616a', green: '#a3be8c', yellow: '#ebcb8b', blue: '#81a1c1', magenta: '#b48ead', cyan: '#88c0d0', white: '#eceff4', brightBlack: '#4c566a', brightRed: '#bf616a', brightGreen: '#a3be8c', brightYellow: '#ebcb8b', brightBlue: '#81a1c1', brightMagenta: '#b48ead', brightCyan: '#88c0d0', brightWhite: '#eceff4' },
        solarized: { background: '#002b36', foreground: '#fdf6e3', cursor: '#93a1a1', selection: 'rgba(38, 139, 210, 0.3)', black: '#073642', red: '#dc322f', green: '#859900', yellow: '#b58900', blue: '#268bd2', magenta: '#d33682', cyan: '#2aa198', white: '#eee8d5', brightBlack: '#002b36', brightRed: '#cb4b16', brightGreen: '#586e75', brightYellow: '#657b83', brightBlue: '#839496', brightMagenta: '#6c71c4', brightCyan: '#93a1a1', brightWhite: '#fdf6e3' },
    };
    return themes[theme] || themes.dark;
}

// ==========================================================================
// Status Helpers
// ==========================================================================

function updateConnectionStatus(connected) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    if (connected) { dot.style.background = 'var(--studio-accent-secondary)'; text.textContent = 'Connected'; }
    else { dot.style.background = 'var(--studio-accent-error)'; text.textContent = 'Disconnected'; }
}

function updateBusyStatus(busy) {
    const dot = document.getElementById('connectionDot');
    if (busy) dot.classList.add('busy'); else dot.classList.remove('busy');
}

function updateStatus(message) {
    if (message) document.getElementById('statusMessage').textContent = message;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
        const s = document.createElement('script');
        s.src = src; s.onload = resolve; s.onerror = reject;
        document.head.appendChild(s);
    });
}

// ==========================================================================
// Workspace Save/Load
// ==========================================================================

async function initWorkspace() {
    try {
        const resp = await fetch(`/api/workspace/load?session_id=${state.sessionId}`);
        const data = await resp.json();
        if (data.success && data.workspace) applyWorkspace(data.workspace);
    } catch (e) { /* no saved workspace */ }
    scheduleSave();
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') saveWorkspace();
    });
}

function scheduleSave() {
    if (state.saveTimer) clearInterval(state.saveTimer);
    state.saveTimer = setInterval(saveWorkspace, 30000);
}

async function saveWorkspace() {
    if (!state.connected) return;
    const workspace = {
        theme: state.theme, currentPath: state.currentPath,
        tabs: state.editorTabs.map(t => ({ path: t.path, name: t.name, content: t.content, language: t.language })),
        activeTab: state.activeTab ? state.activeTab.path : null,
        commandHistory: state.commandHistory.slice(-100),
        sessionId: state.sessionId, savedAt: new Date().toISOString(),
    };
    try {
        await fetch('/api/workspace/save', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId, workspace }),
        });
    } catch (e) { /* best-effort */ }
}

function applyWorkspace(ws) {
    if (ws.theme) setTheme(ws.theme);
    if (ws.currentPath) state.currentPath = ws.currentPath;
    if (ws.tabs && ws.tabs.length > 0) {
        ws.tabs.forEach(tab => openEditorTab(tab.path, tab.content, tab.language));
        if (ws.activeTab) switchToTab(ws.activeTab);
    }
    if (ws.commandHistory) state.commandHistory = ws.commandHistory;
}
