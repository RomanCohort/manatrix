/**
 * Manatrix Studio - Editor Module
 *
 * Monaco editor, tabs management, split view, file operations
 */

// ==========================================================================
// Monaco Editor Init
// ==========================================================================

async function initMonaco() {
    return new Promise((resolve, reject) => {
        require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });

        require(['vs/editor/editor.main'], function () {
            const editorContainer = document.getElementById('monaco-editor');

            state.editor = monaco.editor.create(editorContainer, {
                value: getDefaultScript(),
                language: 'python',
                theme: state.theme === 'dark' ? 'vs-dark' : 'vs',
                automaticLayout: true, fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                minimap: { enabled: true, scale: 1 },
                scrollBeyondLastLine: false, lineNumbers: 'on',
                renderWhitespace: 'selection', tabSize: 4, insertSpaces: true,
                wordWrap: 'off', cursorStyle: 'line', cursorBlinking: 'blink',
                smoothScrolling: true, padding: { top: 8, bottom: 8 },
                suggestOnTriggerCharacters: true, quickSuggestions: true,
                scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
            });

            state.editor.onDidChangeCursorPosition(e => {
                document.getElementById('cursorPos').textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
            });

            document.getElementById('welcomeScreen').style.display = 'none';
            document.getElementById('monaco-editor').style.display = 'block';
            resolve();
        });
    });
}

function getDefaultScript() {
    return `# Manatrix Studio - Welcome Script
# Edit here and run with Ctrl+Enter

import subprocess
import sys

# Example: Run a CLI command
result = subprocess.run(
    [sys.executable, "-m", "manatrix.cli", "version"],
    capture_output=True, text=True
)
print(result.stdout)

print("Edit this script and press Ctrl+Enter to run!")
`;
}

// ==========================================================================
// Editor Tabs
// ==========================================================================

function openEditorTab(path, content, language) {
    const name = path.split(/[/\\]/).pop();

    // Check if already open
    const existing = state.editorTabs.find(t => t.path === path);
    if (existing) { switchToTab(path); return; }

    const tab = { path, name, content, language: language || detectLanguage(path), modified: false, viewState: null };
    state.editorTabs.push(tab);
    renderTabs();
    switchToTab(path);

    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('monaco-editor').style.display = 'block';

    if (state.editor) {
        state.editor.onDidChangeModelContent(() => {
            if (state.activeTab) {
                const currentContent = state.editor.getValue();
                const isModified = currentContent !== state.activeTab.content;
                if (state.activeTab.modified !== isModified) {
                    state.activeTab.modified = isModified;
                    renderTabs();
                }
            }
        });
    }
}

function renderTabs() {
    const tabsContainer = document.getElementById('editorTabs');
    tabsContainer.innerHTML = '';

    state.editorTabs.forEach(tab => {
        const div = document.createElement('div');
        div.className = `editor-tab ${tab === state.activeTab ? 'active' : ''} ${tab.modified ? 'modified' : ''}`;
        div.setAttribute('data-tab', tab.path);
        const safeName = escapeHtml(tab.name);
        const safePath = escapeHtml(tab.path);
        div.innerHTML = `
            <span class="editor-tab-icon">${getTabIcon(tab.language)}</span>
            <span class="tab-name">${safeName}</span>
            <span class="editor-tab-close" data-path="${safePath}">&#x2715;</span>
        `;
        div.addEventListener('click', (e) => {
            if (e.target.classList.contains('editor-tab-close')) closeTab(e.target.getAttribute('data-path'));
            else switchToTab(tab.path);
        });
        div.addEventListener('contextmenu', (e) => { e.preventDefault(); showTabContextMenu(e, tab.path); });
        tabsContainer.appendChild(div);
    });
}

function getTabIcon(lang) {
    const icons = { python: '🐍', javascript: '📜', html: '🌐', css: '🎨', json: '📋', r: '📊', shell: '💻', markdown: '📝', jupyter: '📓' };
    return icons[lang] || '📄';
}

function switchToTab(path) {
    const tab = state.editorTabs.find(t => t.path === path);
    if (!tab || !state.editor) return;

    if (state.activeTab) state.activeTab.viewState = state.editor.saveViewState();

    state.activeTab = tab;
    state.editor.setValue(tab.content);
    monaco.editor.setModelLanguage(state.editor.getModel(), tab.language);
    if (tab.viewState) state.editor.restoreViewState(tab.viewState);

    document.querySelectorAll('.editor-tab').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-tab') === path);
    });
}

function closeTab(path) {
    const tab = state.editorTabs.find(t => t.path === path);
    if (tab && tab.modified) {
        if (!confirm(`"${tab.name}" has unsaved changes. Close anyway?`)) return;
    }

    const idx = state.editorTabs.findIndex(t => t.path === path);
    if (idx === -1) return;
    state.editorTabs.splice(idx, 1);

    if (state.editorTabs.length === 0) { showWelcome(); }
    else { const newTab = state.editorTabs[Math.min(idx, state.editorTabs.length - 1)]; switchToTab(newTab.path); }
    renderTabs();
}

function showWelcome() {
    state.activeTab = null;
    if (state.editor) state.editor.setValue('');
    document.getElementById('welcomeScreen').style.display = 'flex';
    document.getElementById('monaco-editor').style.display = 'none';
}

function closeOtherTabs(keepPath) {
    state.editorTabs = state.editorTabs.filter(t => t.path === keepPath);
    if (state.editorTabs.length > 0) switchToTab(keepPath);
    else showWelcome();
    renderTabs();
}

function closeAllTabs() {
    state.editorTabs = []; state.activeTab = null;
    showWelcome(); renderTabs();
}

function closeSavedTabs() {
    state.editorTabs = state.editorTabs.filter(t => t.modified);
    if (state.editorTabs.length > 0) switchToTab(state.editorTabs[0].path);
    else showWelcome();
    renderTabs();
}

function showTabContextMenu(event, path) {
    const existing = document.getElementById('tabContextMenu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.id = 'tabContextMenu';
    const items = [
        { label: 'Close', action: () => closeTab(path) },
        { label: 'Close Others', action: () => closeOtherTabs(path) },
        { label: 'Close All', action: closeAllTabs },
        { label: 'Close Saved', action: closeSavedTabs },
        { label: '---' },
        { label: 'Copy Path', action: () => { navigator.clipboard.writeText(path); updateStatus('Path copied'); } },
        { label: 'Save', action: () => { switchToTab(path); saveFile(); } },
    ];

    items.forEach(item => {
        if (item.label === '---') {
            const hr = document.createElement('div'); hr.className = 'context-menu-separator'; menu.appendChild(hr); return;
        }
        const el = document.createElement('div'); el.className = 'context-menu-item'; el.textContent = item.label;
        el.addEventListener('click', () => { menu.remove(); item.action(); });
        menu.appendChild(el);
    });

    menu.style.cssText = `position:fixed;left:${event.clientX}px;top:${event.clientY}px;background:var(--studio-bg-secondary);border:1px solid var(--studio-border);border-radius:6px;z-index:9999;min-width:160px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.4);`;
    document.body.appendChild(menu);
    setTimeout(() => {
        document.addEventListener('click', function handler(e) {
            if (!menu.contains(e.target)) { menu.remove(); document.removeEventListener('click', handler); }
        });
    }, 50);
}

function detectLanguage(path) {
    const ext = path.split('.').pop().toLowerCase();
    const map = { py: 'python', js: 'javascript', ts: 'typescript', html: 'html', css: 'css', json: 'json', md: 'markdown', sh: 'shell', r: 'r', ipynb: 'json' };
    return map[ext] || 'plaintext';
}

// ==========================================================================
// File Operations
// ==========================================================================

async function openFile(path) {
    try {
        const resp = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
        const data = await resp.json();
        if (data.content !== undefined) openEditorTab(path, data.content, data.language);
    } catch (e) { console.error('Failed to open file:', e); }
}

async function newFile() {
    const name = prompt('File name:', 'untitled.py');
    if (!name) return;
    openEditorTab(state.currentPath + '/' + name, '', detectLanguage(name));
}

function openFileDialog() {
    const input = document.createElement('input');
    input.type = 'file';
    input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) { const content = await file.text(); openEditorTab(file.name, content, detectLanguage(file.name)); }
    });
    input.click();
}

async function saveFile() {
    if (!state.activeTab || !state.editor) return;
    const content = state.editor.getValue();
    const tab = state.activeTab;

    try {
        const resp = await fetch('/api/files/save', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: tab.path, content }),
        });
        const data = await resp.json();
        if (data.success) {
            tab.content = content; tab.modified = false;
            renderTabs(); updateStatus(`Saved: ${tab.name}`);
        } else { updateStatus(`Save failed: ${data.error}`); }
    } catch (e) { updateStatus(`Save error: ${e}`); }
}

// ==========================================================================
// Run Selection
// ==========================================================================

function runEditorSelection() {
    if (!state.editor) return;
    const selection = state.editor.getSelection();
    let code = state.editor.getModel().getValueInRange(selection);
    if (!code.trim()) {
        const pos = state.editor.getPosition();
        code = state.editor.getModel().getLineContent(pos.lineNumber);
    }
    if (!code.trim()) return;

    state.terminal.write('\r\n');
    state.terminal.write('\x1b[1;36m> \x1b[0m' + code + '\r\n');

    if (state.replMode === 'python') {
        runPythonCode(code);
    } else if (state.replMode === 'shell') {
        runShellCommand(code);
    } else {
        sendCommand(code);
    }
}

async function runPythonCode(code) {
    // Use browser-based Pyodide for parallel execution
    if (window.runPyodideCode && state.pyodideReady) {
        await runPyodideCode(code);
    } else if (window.runPyodideCode) {
        state.terminal.write('\r\n\x1b[33m[*] Initializing Python runtime...\x1b[0m\r\n');
        try {
            await initPyodide();
            await runPyodideCode(code);
        } catch (e) {
            state.terminal.write(`\x1b[31mPyodide failed: ${e}\x1b[0m\r\n`);
            state.terminal.write('\x1b[33mTrying server-side execution...\x1b[0m\r\n');
            await runPythonCodeServer(code);
        }
    } else {
        await runPythonCodeServer(code);
    }
}

async function runPythonCodeServer(code) {
    try {
        const resp = await fetch('/api/repl/python', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });
        const data = await resp.json();
        if (data.stdout) state.terminal.write(data.stdout.replace(/\n/g, '\r\n'));
        if (data.stderr) state.terminal.write('\x1b[31m' + data.stderr.replace(/\n/g, '\r\n\x1b[31m'));
    } catch (e) { state.terminal.write('\x1b[31mError: ' + e + '\x1b[0m\r\n'); }
}

async function runShellCommand(cmd) {
    try {
        const resp = await fetch('/api/repl/shell', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd }),
        });
        const data = await resp.json();
        if (data.stdout) state.terminal.write(highlightTerminalOutput(data.stdout).replace(/\n/g, '\r\n'));
        if (data.stderr) state.terminal.write('\x1b[31m' + data.stderr.replace(/\n/g, '\r\n\x1b[31m'));
    } catch (e) { state.terminal.write('\x1b[31mError: ' + e + '\x1b[0m\r\n'); }
}

// ==========================================================================
// Split Editor
// ==========================================================================

function splitEditor(mode) {
    if (mode === state.splitMode) { unsplitEditor(); return; }

    state.splitMode = mode;
    const panel = document.getElementById('editorPanel');
    panel.classList.add('split-view');

    if (mode === 'horizontal') {
        panel.innerHTML = `
            <div class="split-pane split-pane-1" id="splitPane1">
                <div class="editor-tabs" id="editorTabs1"></div>
                <div class="editor-content" id="editorContent1">
                    <div id="monaco-editor"></div>
                </div>
            </div>
            <div class="split-divider" id="splitDivider"></div>
            <div class="split-pane split-pane-2" id="splitPane2">
                <div class="editor-tabs" id="editorTabs2"></div>
                <div class="editor-content" id="editorContent2">
                    <div id="monaco-editor-2"></div>
                </div>
            </div>
        `;

        renderSplitTabs();
        setTimeout(() => {
            if (document.getElementById('monaco-editor-2') && !state.editor2) {
                state.editor2 = monaco.editor.create(document.getElementById('monaco-editor-2'), {
                    value: '', language: 'python',
                    theme: state.theme === 'dark' ? 'vs-dark' : 'vs',
                    automaticLayout: true, fontSize: 13,
                    fontFamily: "'JetBrains Mono', monospace",
                });
            }
            if (state.editor) state.editor.layout();
            if (state.editor2) state.editor2.layout();
        }, 100);
        initSplitDivider();
    }
    updateStatus(`Split view: ${mode}`);
}

function unsplitEditor() {
    state.splitMode = 'none';
    const panel = document.getElementById('editorPanel');
    panel.classList.remove('split-view');
    panel.innerHTML = `
        <div class="editor-tabs" id="editorTabs"></div>
        <div class="editor-content" id="editorContent">
            <div class="editor-placeholder" id="welcomeScreen" style="display: ${state.editorTabs.length ? 'none' : 'flex'};">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                <h3>Manatrix Studio</h3>
                <p>Edit code and press Ctrl+Enter to run</p>
            </div>
            <div id="monaco-editor" style="display: ${state.editorTabs.length ? 'block' : 'none'};"></div>
        </div>
    `;
    renderTabs();
    if (state.editor) state.editor.layout();
    if (state.editor2) { state.editor2.dispose(); state.editor2 = null; }
    updateStatus('Single view');
}

function renderSplitTabs() {
    ['editorTabs1', 'editorTabs2'].forEach((containerId, paneIdx) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        state.editorTabs.forEach(tab => {
            const div = document.createElement('div');
            div.className = `editor-tab ${tab === state.activeTab ? 'active' : ''}`;
            div.innerHTML = `<span>${getTabIcon(tab.language)} ${escapeHtml(tab.name)}</span>`;
            div.addEventListener('click', () => {
                if (paneIdx === 0) switchToTab(tab.path);
                else if (state.editor2) {
                    state.editor2.setValue(tab.content);
                    monaco.editor.setModelLanguage(state.editor2.getModel(), tab.language);
                }
            });
            container.appendChild(div);
        });
    });
}

function initSplitDivider() {
    const divider = document.getElementById('splitDivider');
    if (!divider) return;
    let dragging = false;
    divider.addEventListener('mousedown', () => { dragging = true; });
    document.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        const container = document.getElementById('editorPanel');
        const rect = container.getBoundingClientRect();
        const pct = ((e.clientX - rect.left) / rect.width) * 100;
        if (pct > 20 && pct < 80) {
            document.getElementById('splitPane1').style.width = pct + '%';
            document.getElementById('splitPane2').style.left = pct + '%';
            if (state.editor) state.editor.layout();
            if (state.editor2) state.editor2.layout();
        }
    });
    document.addEventListener('mouseup', () => { dragging = false; });
}
