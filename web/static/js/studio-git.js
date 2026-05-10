/**
 * Manatrix Studio - Git Panel Module
 *
 * Git status, commit, pull, push operations
 */

// ==========================================================================
// Git Panel
// ==========================================================================

async function initGitPanel() {
    // Git section toggle
    const header = document.getElementById('gitSectionHeader');
    const content = document.getElementById('gitSectionContent');
    if (header && content) {
        header.addEventListener('click', () => {
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        });
    }

    // Git action buttons
    document.getElementById('gitPullBtn')?.addEventListener('click', gitPull);
    document.getElementById('gitPushBtn')?.addEventListener('click', gitPush);
    document.getElementById('gitCommitBtn')?.addEventListener('click', gitCommit);

    // Initial load
    await refreshGitStatus();
}

async function refreshGitStatus() {
    try {
        const resp = await fetch('/api/git/status');
        const data = await resp.json();

        if (!data.success) {
            document.getElementById('gitSection').style.display = 'none';
            return;
        }

        document.getElementById('gitSection').style.display = 'block';
        document.getElementById('gitBranch').textContent = data.branch || 'main';

        const ab = document.getElementById('gitAheadBehind');
        ab.textContent = '';
        if (data.ahead > 0) ab.textContent += ` \u2191${data.ahead}`;
        if (data.behind > 0) ab.textContent += ` \u2193${data.behind}`;

        // Render files
        const filesEl = document.getElementById('gitFiles');
        if (data.files.length === 0) {
            filesEl.innerHTML = '<div class="git-files-header">CHANGES</div><div class="git-file" style="color:var(--studio-text-muted);padding:8px 12px;">Working tree clean</div>';
        } else {
            let html = '<div class="git-files-header">CHANGES</div>';
            data.files.forEach(f => {
                let icon = 'M';
                let cls = 'modified';
                if (f.untracked) { icon = '?'; cls = 'untracked'; }
                else if (f.status.includes('A') || f.status[0] === 'A') { icon = '+'; cls = 'added'; }
                else if (f.status.includes('D') || f.status[0] === 'D') { icon = '-'; cls = 'deleted'; }
                const escapedPath = escapeHtml(f.path);
                const escapedName = escapeHtml(f.path.split(/[/\\]/).pop());
                html += `<div class="git-file" data-path="${escapedPath}">
                    <span class="git-file-status ${cls}">${icon}</span>
                    <span class="git-file-name">${escapedName}</span>
                </div>`;
            });
            filesEl.innerHTML = html;
        }
    } catch (e) {
        document.getElementById('gitSection').style.display = 'none';
    }
}

async function gitPull() {
    state.terminal.write('\r\n\x1b[33m[*] Running git pull...\x1b[0m\r\n');
    try {
        const resp = await fetch('/api/git/pull', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            state.terminal.write('\x1b[32m[+] Pull successful:\x1b[0m ' + data.output.replace(/\n/g, '\r\n'));
            await refreshGitStatus();
        } else {
            state.terminal.write('\x1b[31m[-] Pull failed: ' + data.error + '\x1b[0m\r\n');
        }
    } catch (e) {
        state.terminal.write('\x1b[31m[-] Error: ' + e + '\x1b[0m\r\n');
    }
}

async function gitPush() {
    state.terminal.write('\r\n\x1b[33m[*] Running git push...\x1b[0m\r\n');
    try {
        const resp = await fetch('/api/git/push', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            state.terminal.write('\x1b[32m[+] Push successful:\x1b[0m\r\n');
            await refreshGitStatus();
        } else {
            state.terminal.write('\x1b[31m[-] Push failed: ' + data.error + '\x1b[0m\r\n');
        }
    } catch (e) {
        state.terminal.write('\x1b[31m[-] Error: ' + e + '\x1b[0m\r\n');
    }
}

async function gitCommit() {
    const message = prompt('Commit message:');
    if (!message) return;

    state.terminal.write('\r\n\x1b[33m[*] Creating commit...\x1b[0m\r\n');
    try {
        const resp = await fetch('/api/git/commit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const data = await resp.json();
        if (data.success) {
            state.terminal.write('\x1b[32m[+] Commit created:\x1b[0m ' + data.output.replace(/\n/g, '\r\n'));
            await refreshGitStatus();
        } else {
            state.terminal.write('\x1b[31m[-] Commit failed: ' + data.error + '\x1b[0m\r\n');
        }
    } catch (e) {
        state.terminal.write('\x1b[31m[-] Error: ' + e + '\x1b[0m\r\n');
    }
}