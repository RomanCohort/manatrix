/**
 * Manatrix Studio - Bootstrap
 *
 * Module loading order:
 *   1. studio-core.js       — state, theme, helpers, workspace
 *   2. studio-terminal.js   — xterm, WebSocket bridge, REPL, recording, charts
 *   3. studio-editor.js     — Monaco, tabs, split view, file operations
 *   4. studio-files.js      — file tree, panels, session state sync
 *   5. studio-git.js        — git panel
 *   6. studio-snippets.js   — snippet manager
 *   7. studio-search.js     — global search panel
 *   8. studio-report.js     — report generator
 *   9. studio-misc.js       — tutorial, wordlist analyzer, enhanced WS, recording init
 *  10. studio.js (this file) — keyboard shortcuts, command palette, toolbar, menu bar, init
 */

// ==========================================================================
// Command Palette
// ==========================================================================

function initCommandPalette() {
    const palette = document.getElementById('commandPalette');
    const input = document.getElementById('paletteInput');
    const list = document.getElementById('paletteList');

    const commands = [
        { name: 'New File', desc: 'Ctrl+N', action: newFile },
        { name: 'Open File', desc: 'Ctrl+O', action: openFileDialog },
        { name: 'Save File', desc: 'Ctrl+S', action: saveFile },
        { name: 'Run Selection', desc: 'Ctrl+Enter', action: runEditorSelection },
        { name: 'Clear Console', desc: 'Ctrl+L', action: clearConsole },
        { name: 'Toggle Theme', desc: 'Ctrl+T', action: toggleTheme },
        { name: 'Command Palette', desc: 'Ctrl+Shift+P', action: () => togglePalette(true) },
        { name: 'Refresh Files', desc: '', action: refreshFileTree },
        { name: 'Show Help', desc: '', action: () => showOutputTab('help') },
        { name: 'Generate Bar Chart', desc: '', action: () => runChartCmd('bar') },
        { name: 'Generate Line Chart', desc: '', action: () => runChartCmd('line') },
        { name: 'Generate Pie Chart', desc: '', action: () => runChartCmd('pie') },
        { name: 'CVE Search', desc: '', action: () => sendCommand('cve --search log4j') },
        { name: 'Show ATT&CK', desc: '', action: () => sendCommand('attack-pattern --tactics') },
        { name: 'Demo Chart', desc: '', action: () => sendCommand('demo chart') },
        { name: 'Split Editor Horizontal', desc: 'Ctrl+\\', action: () => splitEditor('horizontal') },
        { name: 'Split Editor Vertical', desc: 'Ctrl+Alt+\\', action: () => splitEditor('vertical') },
        { name: 'Unsplit Editor', desc: '', action: unsplitEditor },
        { name: 'Snippet Manager', desc: 'Ctrl+Shift+S', action: showSnippetManager },
        { name: 'Git Pull', desc: '', action: gitPull },
        { name: 'Git Push', desc: '', action: gitPush },
        { name: 'Git Commit', desc: '', action: gitCommit },
        { name: 'Git Status', desc: '', action: refreshGitStatus },
    ];

    function renderCommands(filter) {
        list.innerHTML = '';
        const all = [...commands, ...(window.studioCommands || [])];
        const filtered = filter
            ? all.filter(c => c.name.toLowerCase().includes(filter.toLowerCase()))
            : all;

        for (const cmd of filtered) {
            const item = document.createElement('div');
            item.className = 'command-palette-item';
            item.innerHTML = `
                <span class="command-palette-item-name">${cmd.name}</span>
                <span class="command-palette-item-desc">${cmd.desc}</span>
            `;
            item.addEventListener('click', () => {
                cmd.action();
                togglePalette(false);
            });
            list.appendChild(item);
        }
    }

    input.addEventListener('input', () => renderCommands(input.value));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') togglePalette(false);
    });

    renderCommands('');
}

function togglePalette(show) {
    const palette = document.getElementById('commandPalette');
    const input = document.getElementById('paletteInput');

    if (show) {
        palette.classList.remove('hidden');
        input.focus();
        input.value = '';
    } else {
        palette.classList.add('hidden');
    }
}

// ==========================================================================
// Keyboard Shortcuts
// ==========================================================================

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const ctrl = e.ctrlKey || e.metaKey;
        const shift = e.shiftKey;
        const alt = e.altKey;

        // Command Palette
        if (ctrl && shift && e.key === 'P') { e.preventDefault(); togglePalette(true); return; }
        if (ctrl && e.key === 'p') { e.preventDefault(); togglePalette(true); return; }

        // Run from editor (Ctrl+Enter)
        if (ctrl && e.key === 'Enter') { e.preventDefault(); runEditorSelection(); return; }

        // Save (Ctrl+S)
        if (ctrl && e.key === 's' && !shift) { e.preventDefault(); saveFile(); return; }

        // New file (Ctrl+N)
        if (ctrl && e.key === 'n') { e.preventDefault(); newFile(); return; }

        // Open (Ctrl+O)
        if (ctrl && e.key === 'o') { e.preventDefault(); openFileDialog(); return; }

        // Clear console (Ctrl+L)
        if (ctrl && e.key === 'l') { e.preventDefault(); clearConsole(); return; }

        // Toggle theme (Ctrl+T)
        if (ctrl && e.key === 't') { e.preventDefault(); toggleTheme(); return; }

        // Toggle sidebar left (Ctrl+B)
        if (ctrl && e.key === 'b') { e.preventDefault(); toggleSidebar('left'); return; }

        // Toggle console (Ctrl+J)
        if (ctrl && e.key === 'j') { e.preventDefault(); toggleConsole(); return; }

        // Toggle right sidebar (Ctrl+5)
        if (ctrl && e.key === '5') { e.preventDefault(); toggleSidebar('right'); return; }

        // Duplicate line (Ctrl+D)
        if (ctrl && !shift && e.key === 'd') {
            if (state.editor) {
                e.preventDefault();
                const pos = state.editor.getPosition();
                const line = state.editor.getModel().getLineContent(pos.lineNumber);
                state.editor.getModel().insertLineAt(pos.lineNumber + 1, line);
                state.editor.setPosition({ lineNumber: pos.lineNumber + 1, column: pos.column });
            }
            return;
        }

        // Delete line (Ctrl+Shift+K)
        if (ctrl && shift && e.key === 'K') {
            if (state.editor) {
                e.preventDefault();
                const pos = state.editor.getPosition();
                state.editor.getModel().deleteLine(pos.lineNumber);
            }
            return;
        }

        // Move line up (Alt+Up)
        if (alt && e.key === 'ArrowUp') {
            if (state.editor) {
                e.preventDefault();
                const pos = state.editor.getPosition();
                if (pos.lineNumber > 1) {
                    const line = state.editor.getModel().getLineContent(pos.lineNumber);
                    state.editor.getModel().deleteLine(pos.lineNumber);
                    state.editor.getModel().insertLineAt(pos.lineNumber - 1, line);
                    state.editor.setPosition({ lineNumber: pos.lineNumber - 1, column: pos.column });
                }
            }
            return;
        }

        // Move line down (Alt+Down)
        if (alt && e.key === 'ArrowDown') {
            if (state.editor) {
                e.preventDefault();
                const pos = state.editor.getPosition();
                const lineCount = state.editor.getModel().getLineCount();
                if (pos.lineNumber < lineCount) {
                    const line = state.editor.getModel().getLineContent(pos.lineNumber);
                    state.editor.getModel().deleteLine(pos.lineNumber);
                    state.editor.getModel().insertLineAt(pos.lineNumber + 1, line);
                    state.editor.setPosition({ lineNumber: pos.lineNumber + 1, column: pos.column });
                }
            }
            return;
        }

        // Focus terminal (Ctrl+2)
        if (ctrl && e.key === '2') { e.preventDefault(); document.getElementById('consoleContent')?.focus(); return; }

        // Focus editor (Ctrl+1)
        if (ctrl && e.key === '1') { e.preventDefault(); if (state.editor) state.editor.focus(); return; }

        // Focus output (Ctrl+3)
        if (ctrl && e.key === '3') { e.preventDefault(); showOutputTab('output'); return; }

        // Toggle file browser (Ctrl+4)
        if (ctrl && e.key === '4') { e.preventDefault(); toggleSidebar('left'); return; }

        // Close tab (Ctrl+W)
        if (ctrl && e.key === 'w') { e.preventDefault(); if (state.activeTab) closeTab(state.activeTab.path); return; }

        // Find (Ctrl+F)
        if (ctrl && e.key === 'f') {
            if (state.editor) { e.preventDefault(); state.editor.getAction('actions.find').run(); }
            return;
        }

        // Replace (Ctrl+H)
        if (ctrl && e.key === 'h') {
            if (state.editor) { e.preventDefault(); state.editor.getAction('editor.action.startFindReplaceAction').run(); }
            return;
        }

        // Toggle comment (Ctrl+/)
        if (ctrl && e.key === '/') {
            if (state.editor) { e.preventDefault(); state.editor.getAction('editor.action.commentLine').run(); }
            return;
        }

        // Next tab (Ctrl+Tab)
        if (ctrl && e.key === 'Tab' && !shift) {
            e.preventDefault();
            if (state.editorTabs.length > 1) {
                const idx = state.editorTabs.findIndex(t => t.path === (state.activeTab && state.activeTab.path));
                const next = (idx + 1) % state.editorTabs.length;
                switchToTab(state.editorTabs[next].path);
            }
            return;
        }

        // Previous tab (Ctrl+Shift+Tab)
        if (ctrl && shift && e.key === 'Tab') {
            e.preventDefault();
            if (state.editorTabs.length > 1) {
                const idx = state.editorTabs.findIndex(t => t.path === (state.activeTab && state.activeTab.path));
                const prev = (idx - 1 + state.editorTabs.length) % state.editorTabs.length;
                switchToTab(state.editorTabs[prev].path);
            }
            return;
        }

        // Split horizontal (Ctrl+\)
        if (ctrl && e.key === '\\') {
            e.preventDefault();
            splitEditor(state.splitMode === 'horizontal' ? 'none' : 'horizontal');
            return;
        }

        // Escape to close palette
        if (e.key === 'Escape') togglePalette(false);

        // F1 = Command Palette
        if (e.key === 'F1') { e.preventDefault(); togglePalette(true); }
    });
}

// ==========================================================================
// Toolbar & Menu Bar
// ==========================================================================

function initToolbar() {
    document.getElementById('runBtn')?.addEventListener('click', runEditorSelection);
    document.getElementById('newFileBtn')?.addEventListener('click', newFile);
    document.getElementById('openFileBtn')?.addEventListener('click', openFileDialog);
    document.getElementById('saveBtn')?.addEventListener('click', saveFile);
    document.getElementById('stopBtn')?.addEventListener('click', interruptCommand);
    document.getElementById('clearConsoleBtn')?.addEventListener('click', clearConsole);
    document.getElementById('interruptBtn')?.addEventListener('click', interruptCommand);
    document.getElementById('clearHistoryBtn')?.addEventListener('click', clearHistory);
    document.getElementById('clearPlotsBtn')?.addEventListener('click', clearCharts);
}

function initMenuBar() {
    document.querySelectorAll('.menubar-item').forEach(item => {
        item.addEventListener('click', () => {
            const menu = item.getAttribute('data-menu');
            showMenu(menu, item);
        });
    });
}

function showMenu(menu, element) {
    const actions = {
        file: () => newFile(),
        edit: () => { if (state.editor) state.editor.focus(); },
        view: () => toggleTheme(),
        run: () => runEditorSelection(),
        tools: () => togglePalette(true),
        help: () => showOutputTab('help'),
    };
    if (actions[menu]) actions[menu]();
}

// ==========================================================================
// Helpers
// ==========================================================================

function interruptCommand() {
    if (!state.busy) return;
    fetch(`/api/terminal/interrupt/${state.sessionId}`, { method: 'POST' })
        .then(() => {
            state.terminal.write('\r\n\x1b[33m[!] Interrupted\x1b[0m\r\n');
            state.busy = false;
            updateBusyStatus(false);
        });
}

function runChartCmd(type) {
    sendCommand(`chart --type ${type} --x "A,B,C,D,E" --y "10,20,30,40,50" --output /tmp/chart_${type}.png`);
}

// ==========================================================================
// Fallback Handlers (Polyfill)
// ==========================================================================

// Provide fallback for any missing functions
function ensureFunctions() {
    // Git functions
    if (typeof gitPull === 'undefined') {
        window.gitPull = async function() {
            state.terminal.write('\x1b[33m[*] Git pull not available\x1b[0m\r\n');
        };
    }
    if (typeof gitPush === 'undefined') {
        window.gitPush = async function() {
            state.terminal.write('\x1b[33m[*] Git push not available\x1b[0m\r\n');
        };
    }
    if (typeof gitCommit === 'undefined') {
        window.gitCommit = async function() {
            state.terminal.write('\x1b[33m[*] Git commit not available\x1b[0m\r\n');
        };
    }
    if (typeof refreshGitStatus === 'undefined') {
        window.refreshGitStatus = async function() {
            // Silent refresh
        };
    }

    // File functions
    if (typeof clearHistory === 'undefined') {
        window.clearHistory = function() {
            const panel = document.getElementById('historyPanel');
            if (panel) panel.innerHTML = '<div class="history-item" style="color:var(--studio-text-muted);font-style:italic;">No history yet</div>';
        };
    }

    // Ensure newFolder creates actual folders
    if (typeof newFolder === 'function') {
        const origNewFolder = newFolder;
        window.newFolder = async function() {
            const name = prompt('Folder name:');
            if (!name) return;
            try {
                const resp = await fetch('/api/files/new', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: state.currentPath + '/' + name, is_dir: true, content: '' }),
                });
                await refreshFileTree();
                updateStatus(`Created folder: ${name}`);
            } catch (e) {
                updateStatus(`Failed to create folder: ${e}`);
            }
        };
    }
}

// ==========================================================================
// Global Exports (for HTML onclick handlers)
// ==========================================================================

window.showSnippetManager = showSnippetManager;

// ==========================================================================
// Additional Commands for Palette
// ==========================================================================

window.studioCommands = [
    { name: 'Global Search', desc: 'Ctrl+Shift+F', action: showSearchPanel },
    { name: 'Report Generator', desc: '', action: showReportGenerator },
    { name: 'Wordlist Analyzer', desc: '', action: showWordlistAnalyzer },
    { name: 'Start Recording', desc: '', action: startRecording },
    { name: 'Stop Recording', desc: '', action: stopRecording },
    { name: 'List Recordings', desc: '', action: listRecordings },
    { name: 'Play Recording', desc: '', action: () => { const id = prompt('Recording ID:'); if (id) playRecording(id); } },
    { name: 'Start Tutorial', desc: '', action: startTutorial },
];

// ==========================================================================
// Bootstrap
// ==========================================================================

async function bootstrap() {
    try {
        // Core
        initTheme();

        // Terminal & Connection
        await initTerminal();
        initWebSocket();

        // Editor
        await initMonaco();

        // File tree & Panels
        await initFileTree();
        initPanels();

        // Git, Snippets
        initGitPanel();
        initReplMode();
        initSnippetManager();

        // UI features
        initKeyboardShortcuts();
        initCommandPalette();
        initToolbar();
        initMenuBar();

        // Workspace persistence
        initWorkspace();

        // Extra features
        initGlobalSearch();
        initRecording();
        initTutorial();

        // Ensure all functions are defined
        ensureFunctions();

        updateStatus();
        console.log('[Studio] Bootstrap complete');
    } catch (err) {
        console.error('[Studio] Bootstrap error:', err);
    }
}

// Use both DOMContentLoaded and a fallback for Electron's timing
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
} else {
    // DOM already loaded, bootstrap immediately
    bootstrap();
}
