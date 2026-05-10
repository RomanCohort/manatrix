/**
 * Manatrix Studio - Report Generator Module
 *
 * Generate penetration test reports (HTML/Markdown)
 */

// ==========================================================================
// Report Generator Panel
// ==========================================================================

function showReportGenerator() {
    const existing = document.getElementById('reportPanel');
    if (existing) { existing.remove(); return; }

    const panel = document.createElement('div');
    panel.id = 'reportPanel';
    panel.innerHTML = `
        <div class="report-header">
            <h3>Generate Report</h3>
            <button onclick="this.closest('#reportPanel').remove()">&#x2715;</button>
        </div>
        <div class="report-body">
            <label>Title: <input type="text" id="reportTitle" value="Penetration Test Report" style="width:100%;margin:4px 0;"></label>
            <label>Template:
                <select id="reportTemplate" style="width:100%;margin:4px 0;">
                    <option value="technical">Technical Report</option>
                    <option value="executive">Executive Summary</option>
                    <option value="vulnerability">Vulnerability Assessment</option>
                </select>
            </label>
            <label>Format:
                <select id="reportFormat" style="width:100%;margin:4px 0;">
                    <option value="html">HTML</option>
                    <option value="markdown">Markdown</option>
                </select>
            </label>
            <div id="reportFindings">
                <button id="addFindingBtn">+ Add Finding</button>
            </div>
            <button id="generateReportBtn" style="width:100%;padding:10px;background:var(--studio-accent-primary);color:white;border:none;border-radius:4px;cursor:pointer;margin-top:10px;">Generate Report</button>
        </div>
    `;
    panel.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:500px;max-height:80vh;background:var(--studio-bg-secondary);border:1px solid var(--studio-border);border-radius:8px;z-index:9999;overflow:hidden;';

    document.body.appendChild(panel);

    let findingCount = 0;
    document.getElementById('addFindingBtn').onclick = () => {
        findingCount++;
        const div = document.createElement('div');
        div.className = 'finding-entry';
        div.style.cssText = 'background:var(--studio-bg-tertiary);padding:8px;margin:8px 0;border-radius:4px;';
        // Create elements safely to avoid XSS
        const titleInput = document.createElement('input');
        titleInput.placeholder = 'Finding Title';
        titleInput.className = 'finding-title';
        titleInput.style.width = '100%';
        const descTextarea = document.createElement('textarea');
        descTextarea.placeholder = 'Description';
        descTextarea.className = 'finding-desc';
        descTextarea.style.width = '100%';
        descTextarea.style.height = '50px';
        descTextarea.style.marginTop = '4px';
        const severitySelect = document.createElement('select');
        severitySelect.className = 'finding-severity';
        severitySelect.style.marginTop = '4px';
        ['Critical', 'High', 'Medium', 'Low'].forEach((sev, i) => {
            const opt = document.createElement('option');
            opt.value = sev;
            opt.textContent = sev;
            if (sev === 'Medium') opt.selected = true;
            severitySelect.appendChild(opt);
        });
        div.appendChild(titleInput);
        div.appendChild(descTextarea);
        div.appendChild(severitySelect);
        document.getElementById('reportFindings').appendChild(div);
    };

    document.getElementById('generateReportBtn').onclick = async () => {
        const title = document.getElementById('reportTitle').value;
        const template = document.getElementById('reportTemplate').value;
        const format = document.getElementById('reportFormat').value;

        const findings = [];
        document.querySelectorAll('.finding-entry').forEach(el => {
            findings.push({
                title: el.querySelector('.finding-title').value,
                description: el.querySelector('.finding-desc').value,
                severity: el.querySelector('.finding-severity').value,
                status: 'Open',
            });
        });

        const resp = await fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, template, format, findings }),
        });
        const data = await resp.json();

        if (data.success) {
            state.terminal.write(`\r\n\x1b[32m[+] Report generated: ${data.path}\x1b[0m\r\n`);
            panel.remove();
            window.open(data.path, '_blank');
        } else {
            alert('Error: ' + data.error);
        }
    };
}

function generateReport(title, template, format, findings) {
    return fetch('/api/report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, template, format, findings }),
    }).then(r => r.json());
}