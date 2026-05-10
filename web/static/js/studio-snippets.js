/**
 * Manatrix Studio - Snippets Module
 *
 * Code snippet manager: browse, search, insert snippets
 */

// ==========================================================================
// Snippet Manager
// ==========================================================================

let snippetCache = null;

async function initSnippetManager() {
    const commands = [
        { name: 'Open Snippet Manager', desc: 'Manage code snippets', action: showSnippetManager },
        { name: 'Insert Snippet...', desc: 'Insert snippet at cursor', action: insertSnippetPrompt },
    ];

    if (window.studioCommands) window.studioCommands.push(...commands);

    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            showSnippetManager();
        }
    });
}

async function showSnippetManager() {
    togglePalette(false);

    if (!snippetCache) {
        try {
            const resp = await fetch('/api/snippets');
            const data = await resp.json();
            snippetCache = data.snippets || {};
        } catch (e) {
            snippetCache = {};
        }
    }

    const categories = Object.keys(snippetCache);
    let html = `
        <div class="snippet-manager">
            <div class="snippet-header">
                <span>Code Snippets</span>
                <button class="snippet-close" onclick="this.closest('.snippet-manager').remove()">&#x2715;</button>
            </div>
            <div class="snippet-search">
                <input type="text" id="snippetSearch" placeholder="Search snippets..." style="width:100%;padding:8px;background:var(--studio-bg-tertiary);border:1px solid var(--studio-border);color:var(--studio-text-primary);border-radius:4px;">
            </div>
            <div class="snippet-content" id="snippetContent">
    `;

    categories.forEach(cat => {
        html += `<div class="snippet-category">
            <div class="snippet-cat-header">${cat.toUpperCase()}</div>`;
        snippetCache[cat].forEach(s => {
            const escapedName = escapeHtml(s.name);
            const escapedDesc = escapeHtml(s.desc || '');
            html += `<div class="snippet-item" data-code="${encodeURIComponent(s.code)}" data-cat="${cat}">
                <span class="snippet-name">${escapedName}</span>
                <span class="snippet-desc">${escapedDesc}</span>
            </div>`;
        });
        html += '</div>';
    });

    html += '</div></div>';

    document.querySelector('.snippet-manager')?.remove();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay active';
    overlay.innerHTML = html;
    overlay.style.cssText = 'align-items:flex-start;justify-content:center;padding-top:60px;';

    const modal = overlay.querySelector('.snippet-manager');
    modal.style.cssText = 'background:var(--studio-bg-secondary);border:1px solid var(--studio-border);border-radius:8px;max-width:500px;width:90%;max-height:70vh;overflow:hidden;display:flex;flex-direction:column;';

    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('snippetSearch')?.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        document.querySelectorAll('.snippet-item').forEach(item => {
            const name = item.querySelector('.snippet-name').textContent.toLowerCase();
            const desc = item.querySelector('.snippet-desc').textContent.toLowerCase();
            item.style.display = (name.includes(q) || desc.includes(q)) ? '' : 'none';
        });
    });

    document.querySelectorAll('.snippet-item').forEach(item => {
        item.addEventListener('click', () => {
            const code = decodeURIComponent(item.getAttribute('data-code'));
            if (state.editor) {
                const pos = state.editor.getPosition();
                state.editor.executeEdits('snippet', [{
                    range: new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column),
                    text: code,
                }]);
                state.editor.setPosition({ lineNumber: pos.lineNumber + code.split('\n').length, column: 1 });
                state.editor.focus();
            }
            overlay.remove();
        });
    });
}

async function insertSnippetPrompt() {
    showSnippetManager();
}