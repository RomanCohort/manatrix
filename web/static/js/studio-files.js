/**
 * Manatrix Studio - Files & Panels Module
 */

// ==========================================================================
// File Tree
// ==========================================================================

async function initFileTree() {
    await refreshFileTree();
    document.getElementById('refreshFilesBtn')?.addEventListener('click', refreshFileTree);
    document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
}

async function refreshFileTree() {
    try {
        const resp = await fetch(`/api/files?path=${encodeURIComponent(state.currentPath)}`);
        const data = await resp.json();
        renderFileTree(data.items || [], data.path);
    } catch (e) { console.error('Failed to load files:', e); }
}

function renderFileTree(items, basePath) {
    const tree = document.getElementById('fileTree');
    tree.innerHTML = '';

    if (basePath && basePath !== '.') {
        const parts = basePath.replace(/\\/g, '/').split('/');
        if (parts.length > 1) {
            parts.pop();
            const parentPath = parts.join('/') || '.';
            const div = document.createElement('div');
            div.className = 'file-item folder';
            div.innerHTML = `<span class="file-icon">&#x1F4C1;</span><span class="file-name">..</span>`;
            div.addEventListener('click', () => { state.currentPath = parentPath; refreshFileTree(); });
            tree.appendChild(div);
        }
    }

    const folders = items.filter(i => i.is_dir);
    const files = items.filter(i => !i.is_dir);

    [...folders, ...files].forEach(item => {
        const div = document.createElement('div');
        const isFolder = item.is_dir;
        const icon = isFolder ? '&#x1F4C1;' : getFileIcon(item.name);
        const escapedName = escapeHtml(item.name);

        div.className = `file-item ${isFolder ? 'folder' : ''}`;
        div.innerHTML = `
            <span class="file-icon ${getFileIconClass(item.name)}">${icon}</span>
            <span class="file-name">${escapedName}</span>
            ${!isFolder ? `<span class="file-size">${formatSize(item.size)}</span>` : ''}
        `;

        div.addEventListener('click', () => {
            if (isFolder) { state.currentPath = item.path; refreshFileTree(); }
            else openFile(item.path);
        });
        tree.appendChild(div);
    });
}

function getFileIconClass(name) {
    const ext = name.split('.').pop().toLowerCase();
    return { py: 'py', js: 'js', ts: 'js', html: 'html', css: 'css', json: 'json', md: 'md' }[ext] || '';
}

function getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    return { py: '🐍', js: '📜', ts: '📜', html: '🌐', css: '🎨', json: '📋', md: '📝', yml: '⚙️', yaml: '⚙️', txt: '📄', log: '📄', png: '🖼️', jpg: '🖼️', svg: '🖼️', ipynb: '📓' }[ext] || '📄';
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'K';
    return (bytes / (1024 * 1024)).toFixed(1) + 'M';
}

async function newFolder() {
    const name = prompt('Folder name:');
    if (!name) return;
    updateStatus(`Created folder: ${name}`);
}

// ==========================================================================
// Panels
// ==========================================================================

function initPanels() {
    document.getElementById('toggleConsoleBtn')?.addEventListener('click', toggleConsole);
    document.getElementById('consoleHeader')?.addEventListener('click', (e) => { if (e.target === document.getElementById('consoleHeader')) toggleConsole(); });
    document.getElementById('refreshEnvBtn')?.addEventListener('click', refreshSessionState);
    document.querySelectorAll('.output-tab').forEach(tab => {
        tab.addEventListener('click', () => showOutputTab(tab.getAttribute('data-tab')));
    });
    document.querySelectorAll('.env-section-header').forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content) content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });
    });
}

function toggleConsole() {
    document.getElementById('consolePanel').classList.toggle('collapsed');
}

function showOutputTab(tabName) {
    document.querySelectorAll('.output-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-tab') === tabName));
    document.querySelectorAll('#outputContent > div').forEach(d => d.classList.add('hidden'));
    const contentMap = { output: 'outputText', plots: 'outputPlots', help: 'outputHelp', trace: 'outputTrace', rendered: 'outputRendered' };
    document.getElementById(contentMap[tabName])?.classList.remove('hidden');
}

function toggleSidebar(side) {
    document.getElementById(side === 'left' ? 'leftSidebar' : 'rightSidebar').classList.toggle('open');
}

// ==========================================================================
// Session State Sync
// ==========================================================================

async function refreshSessionState() {
    if (!state.connected) return;
    try {
        const resp = await fetch(`/api/session/${state.sessionId}/state`);
        const data = await resp.json();

        const varsPanel = document.getElementById('variablesPanel');
        if (varsPanel && data.variables) {
            const entries = Object.entries(data.variables);
            varsPanel.innerHTML = entries.length === 0
                ? '<div class="env-item" style="color:var(--studio-text-muted);font-style:italic;">No variables defined</div>'
                : entries.map(([name, info]) => `<div class="env-item"><span class="env-item-name">$${escapeHtml(name)}</span><span class="env-item-value">${escapeHtml(String(info.value))}</span><span class="env-item-type">${escapeHtml(info.type)}</span></div>`).join('');
        }

        const lastPanel = document.getElementById('lastValuePanel');
        if (lastPanel && data.last_result) lastPanel.innerHTML = `<span class="env-item-value">${escapeHtml(data.last_result)}</span>`;

        const histPanel = document.getElementById('historyPanel');
        if (histPanel && data.history) {
            state.commandHistory = data.history;
            histPanel.innerHTML = data.history.map((cmd, i) => `<div class="history-item"><span class="history-item-num">${i + 1}</span><span class="history-item-cmd">${escapeHtml(cmd)}</span></div>`).reverse().join('');
            histPanel.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', () => {
                    const cmd = item.querySelector('.history-item-cmd').textContent;
                    state.terminal.write('\r\n');
                    printLine(cmd);
                    sendCommand(cmd);
                });
            });
        }
        document.getElementById('statusCwd').textContent = `cwd: ${data.cwd || '--'}`;
    } catch (e) { /* silent fail */ }
}

function clearHistory() {
    document.getElementById('historyPanel').innerHTML = '<div class="history-item" style="color: var(--studio-text-muted); font-style: italic;">No history yet</div>';
}
