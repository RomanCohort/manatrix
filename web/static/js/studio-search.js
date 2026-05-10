/**
 * Manatrix Studio - Search Module
 *
 * Global search/replace panel, Ctrl+Shift+F shortcut
 */

// ==========================================================================
// Global Search Panel
// ==========================================================================

function initGlobalSearch() {
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.key === 'F') {
            e.preventDefault();
            showSearchPanel();
        }
    });
}

function showSearchPanel() {
    togglePalette(false);
    const existing = document.getElementById('searchPanel');
    if (existing) { existing.remove(); return; }

    const panel = document.createElement('div');
    panel.id = 'searchPanel';
    panel.className = 'search-panel';
    panel.innerHTML = `
        <div class="search-header">
            <input type="text" id="searchInput" placeholder="Search in files (Ctrl+Shift+F)..." style="flex:1;">
            <label><input type="checkbox" id="searchCase"> Case</label>
            <label><input type="checkbox" id="searchRegex"> Regex</label>
            <button id="searchBtn">Search</button>
            <button id="searchCloseBtn">&#x2715;</button>
        </div>
        <div class="search-options">
            <input type="text" id="searchPath" placeholder="Path (default: .)" style="width:150px;">
            <span id="searchStatus"></span>
        </div>
        <div class="search-results" id="searchResults"></div>
    `;
    panel.style.cssText = 'position:fixed;top:60px;right:20px;width:500px;max-height:70vh;background:var(--studio-bg-secondary);border:1px solid var(--studio-border);border-radius:8px;z-index:9999;overflow:hidden;display:flex;flex-direction:column;';

    document.body.appendChild(panel);

    document.getElementById('searchCloseBtn').onclick = () => panel.remove();
    document.getElementById('searchBtn').onclick = doSearch;
    document.getElementById('searchInput').onkeydown = (e) => { if (e.key === 'Enter') doSearch(); };

    document.getElementById('searchInput').focus();
}

async function doSearch() {
    const query = document.getElementById('searchInput').value;
    const path = document.getElementById('searchPath').value || '.';
    const caseSensitive = document.getElementById('searchCase').checked;
    const useRegex = document.getElementById('searchRegex').checked;

    document.getElementById('searchStatus').textContent = 'Searching...';
    document.getElementById('searchResults').innerHTML = '';

    try {
        const resp = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, path, case_sensitive: caseSensitive, use_regex: useRegex }),
        });
        const data = await resp.json();

        if (!data.success) {
            document.getElementById('searchStatus').textContent = 'Error: ' + data.error;
            return;
        }

        document.getElementById('searchStatus').textContent = `${data.total} results in ${data.files_searched} files`;

        const resultsEl = document.getElementById('searchResults');
        resultsEl.style.cssText = 'flex:1;overflow:auto;padding:8px;';

        if (data.results.length === 0) {
            resultsEl.innerHTML = '<div style="color:var(--studio-text-muted);text-align:center;padding:20px;">No results</div>';
            return;
        }

        let currentFile = '';
        data.results.forEach(r => {
            if (r.relative_path !== currentFile) {
                currentFile = r.relative_path;
                const fileHeader = document.createElement('div');
                fileHeader.className = 'search-file-header';
                fileHeader.textContent = r.relative_path;
                fileHeader.style.cssText = 'padding:4px 8px;background:var(--studio-bg-tertiary);font-size:11px;color:var(--studio-accent-primary);cursor:pointer;';
                fileHeader.onclick = () => openFile(r.file);
                resultsEl.appendChild(fileHeader);
            }

            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.style.cssText = 'padding:2px 8px;font-size:12px;cursor:pointer;display:flex;gap:8px;';
            // Escape the match for safe regex and escape content for safe HTML
            const escapedMatch = re.escape(r.match);
            const escapedContent = escapeHtml(r.content);
            const highlight = escapedContent.replace(
                new RegExp(escapedMatch, 'gi'),
                '<span style="background:var(--studio-accent-warning);color:black;padding:0 2px;border-radius:2px;">$&</span>'
            );
            const lineSpan = document.createElement('span');
            lineSpan.style.color = 'var(--studio-text-muted)';
            lineSpan.style.minWidth = '40px';
            lineSpan.textContent = r.line + ':';
            const contentSpan = document.createElement('span');
            contentSpan.innerHTML = highlight;
            item.appendChild(lineSpan);
            item.appendChild(contentSpan);
            item.onclick = () => openFile(r.file).then(() => {
                if (state.editor) {
                    state.editor.revealLineInCenter(r.line);
                    state.editor.setPosition({ lineNumber: r.line, column: 1 });
                    const decorations = state.editor.deltaDecorations([], [
                        { range: new monaco.Range(r.line, 1, r.line, 1), options: { isWholeLine: true, className: 'search-highlight-line' } }
                    ]);
                    setTimeout(() => state.editor.deltaDecorations(decorations, []), 2000);
                }
            });
            resultsEl.appendChild(item);
        });
    } catch (e) {
        document.getElementById('searchStatus').textContent = 'Error: ' + e;
    }
}

function closeSearchPanel() {
    document.getElementById('searchPanel')?.remove();
}