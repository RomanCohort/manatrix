/**
 * Manatrix Studio - Autonomous Agent Panel
 *
 * Claude Code-style autonomous attack agent UI.
 * Connects via WebSocket to /ws/attack/{session_id}
 */

(function() {
    'use strict';

    // State
    let agentWs = null;
    let agentSessionId = null;
    let agentRunning = false;
    let actionCount = 0;

    // DOM
    const briefInput = document.getElementById('agentBrief');
    const startBtn = document.getElementById('agentStartBtn');
    const pauseBtn = document.getElementById('agentPauseBtn');
    const stopBtn = document.getElementById('agentStopBtn');
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.getElementById('agentStatusText');
    const progressDiv = document.getElementById('agentProgress');
    const progressFill = document.getElementById('agentProgressFill');
    const progressText = document.getElementById('agentProgressText');
    const actionsList = document.getElementById('agentActionsList');
    const summaryDiv = document.getElementById('agentSummary');
    const hostsEl = document.getElementById('agentHosts');
    const vulnsEl = document.getElementById('agentVulns');
    const credsEl = document.getElementById('agentCreds');
    const shellsEl = document.getElementById('agentShells');

    // Collapsible section
    const sectionHeader = document.getElementById('agentSectionHeader');
    const sectionContent = document.getElementById('agentSectionContent');
    if (sectionHeader) {
        sectionHeader.addEventListener('click', function() {
            const visible = sectionContent.style.display !== 'none';
            sectionContent.style.display = visible ? 'none' : 'block';
            sectionHeader.querySelector('span:last-child').textContent = visible ? '\u25B6' : '\u25BC';
        });
    }

    // Utility: get WebSocket base URL
    function getWsBaseUrl() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${location.host}`;
    }

    // Set agent status
    function setStatus(state, text) {
        statusIndicator.className = 'status-indicator ' + state;
        statusText.textContent = text;
    }

    // Add action to the log
    function addAction(action) {
        actionCount++;
        const icon = action.success ? '\u2713' : '\u2717';
        const cls = action.success ? 'success' : 'failure';
        const div = document.createElement('div');
        div.className = 'agent-action ' + cls;
        div.innerHTML = `
            <span class="agent-action-icon">${icon}</span>
            <span class="agent-action-type">${escapeHtml(action.type || '--')}</span>
            <span class="agent-action-target">${escapeHtml(action.target || '--')}</span>
            <span class="agent-action-duration">${action.duration ? action.duration.toFixed(1) + 's' : ''}</span>
        `;
        // Remove placeholder
        const placeholder = actionsList.querySelector('.agent-action-placeholder');
        if (placeholder) placeholder.remove();
        actionsList.appendChild(div);
        actionsList.scrollTop = actionsList.scrollHeight;
    }

    // Update summary counters
    function updateSummary(data) {
        summaryDiv.style.display = 'flex';
        if (data.hosts !== undefined) hostsEl.textContent = data.hosts;
        if (data.vulns !== undefined) vulnsEl.textContent = data.vulns;
        if (data.creds !== undefined) credsEl.textContent = data.creds;
        if (data.shells !== undefined) shellsEl.textContent = data.shells;
    }

    // Start agent
    function startAgent() {
        const brief = (briefInput.value || '').trim();
        if (!brief) {
            setStatus('error', 'Please enter an attack brief');
            return;
        }

        // Check if LLM is configured
        const apiKey = localStorage.getItem('studio_llm_api_key');
        if (!apiKey) {
            setStatus('error', 'No API key configured');
            const errDiv = document.createElement('div');
            errDiv.className = 'agent-action failure';
            errDiv.innerHTML = `
                <span class="agent-action-icon">\u2717</span>
                <span class="agent-action-type">LLM not configured</span>
                <span class="agent-action-target" style="font-size:10px;">Click the \u2699 Settings button to add your API key</span>
            `;
            const placeholder = actionsList.querySelector('.agent-action-placeholder');
            if (placeholder) placeholder.remove();
            actionsList.appendChild(errDiv);
            return;
        }

        agentSessionId = 'agent_' + Date.now().toString(36);
        actionCount = 0;
        actionsList.innerHTML = '<div class="agent-action-placeholder">Starting...</div>';
        summaryDiv.style.display = 'none';
        hostsEl.textContent = '0';
        vulnsEl.textContent = '0';
        credsEl.textContent = '0';
        shellsEl.textContent = '0';

        // Connect WebSocket
        const wsUrl = getWsBaseUrl() + '/ws/attack/' + agentSessionId;
        try {
            agentWs = new WebSocket(wsUrl);
        } catch (e) {
            setStatus('error', 'WebSocket error: ' + e.message);
            return;
        }

        agentWs.onopen = function() {
            agentRunning = true;
            setStatus('running', 'Running...');
            progressDiv.style.display = 'block';
            progressFill.style.width = '10%';
            progressText.textContent = 'Initializing...';

            startBtn.disabled = true;
            pauseBtn.disabled = false;
            stopBtn.disabled = false;

            // Send start command with LLM config from localStorage
            agentWs.send(JSON.stringify({
                type: 'start',
                brief: brief,
                dry_run: false,
                llm_config: {
                    provider: localStorage.getItem('studio_llm_provider') || 'deepseek',
                    api_key: localStorage.getItem('studio_llm_api_key') || '',
                    model: localStorage.getItem('studio_llm_model') || '',
                    base_url: localStorage.getItem('studio_llm_base_url') || '',
                },
            }));
        };

        agentWs.onmessage = function(event) {
            let msg;
            try {
                msg = JSON.parse(event.data);
            } catch(e) {
                console.error('Failed to parse agent WebSocket message:', e);
                return;
            }

            const type = msg.type;
            const data = msg.data || {};

            switch (type) {
                case 'status':
                    setStatus('running', data.message || 'Running...');
                    progressText.textContent = data.phase || '';
                    break;

                case 'parsed':
                    progressFill.style.width = '20%';
                    progressText.textContent = 'Brief parsed';
                    setStatus('running', 'Plan: ' + (data.targets || []).join(', '));
                    break;

                case 'plan':
                    progressFill.style.width = '30%';
                    const phases = data.total_phases || 0;
                    progressText.textContent = `Plan: ${phases} phases`;
                    break;

                case 'phase_change':
                    const phaseName = data.message || data.phase || '';
                    progressText.textContent = 'Phase: ' + phaseName;
                    break;

                case 'action_start':
                    setStatus('running', `${data.type} -> ${data.target}`);
                    break;

                case 'action_result':
                    addAction({
                        success: data.success,
                        type: data.type,
                        target: data.target,
                        duration: data.duration,
                    });
                    // Update progress
                    const pct = Math.min(90, 30 + actionCount * 8);
                    progressFill.style.width = pct + '%';
                    break;

                case 'action_complete':
                    addAction({
                        success: data.success,
                        type: data.type,
                        target: data.target,
                        duration: data.duration,
                    });
                    break;

                case 'reflection':
                    // Optionally show reflection insights
                    break;

                case 'complete':
                    agentRunning = false;
                    setStatus('complete', 'Complete');
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Attack complete';

                    updateSummary({
                        hosts: data.hosts_discovered,
                        vulns: data.vulns_found,
                        creds: data.creds_obtained,
                        shells: data.shells_obtained,
                    });

                    startBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                    break;

                case 'paused':
                    agentRunning = false;
                    setStatus('paused', 'Paused');
                    break;

                case 'resumed':
                    agentRunning = true;
                    setStatus('running', 'Resumed');
                    break;

                case 'stopped':
                    agentRunning = false;
                    setStatus('idle', 'Stopped');
                    progressFill.style.width = '0%';
                    progressText.textContent = '';
                    startBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                    break;

                case 'interrupted':
                    agentRunning = false;
                    setStatus('idle', 'Interrupted');
                    startBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                    break;

                case 'error':
                    setStatus('error', data.message || 'Error');
                    startBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                    // Show error in actions list
                    const placeholder = actionsList.querySelector('.agent-action-placeholder');
                    if (placeholder) placeholder.remove();
                    const errDiv = document.createElement('div');
                    errDiv.className = 'agent-action failure';
                    errDiv.innerHTML = `
                        <span class="agent-action-icon">\u2717</span>
                        <span class="agent-action-type">ERROR</span>
                        <span class="agent-action-target">${escapeHtml((data.message || 'Error').substring(0, 60))}</span>
                    `;
                    actionsList.appendChild(errDiv);
                    actionsList.scrollTop = actionsList.scrollHeight;
                    break;
            }
        };

        agentWs.onclose = function() {
            if (agentRunning) {
                setStatus('idle', 'Disconnected');
            }
            agentRunning = false;
            startBtn.disabled = false;
            pauseBtn.disabled = true;
            stopBtn.disabled = true;
        };

        agentWs.onerror = function() {
            setStatus('error', 'Connection error');
            agentRunning = false;
            startBtn.disabled = false;
            pauseBtn.disabled = true;
            stopBtn.disabled = true;
        };
    }

    // Pause
    function pauseAgent() {
        if (agentWs && agentRunning) {
            agentWs.send(JSON.stringify({ type: 'pause' }));
        }
    }

    // Stop
    function stopAgent() {
        if (agentWs) {
            agentWs.send(JSON.stringify({ type: 'stop' }));
        }
    }

    // Bind buttons
    if (startBtn) startBtn.addEventListener('click', startAgent);
    if (pauseBtn) pauseBtn.addEventListener('click', pauseAgent);
    if (stopBtn) stopBtn.addEventListener('click', stopAgent);

    // Register with studio if available
    if (window.Studio) {
        window.Studio.agent = {
            start: startAgent,
            pause: pauseAgent,
            stop: stopAgent,
        };

        // Add command palette commands
        if (window.Studio.addPaletteCommand) {
            window.Studio.addPaletteCommand({
                id: 'agent:start',
                label: 'Agent: Start Autonomous Attack',
                action: function() {
                    briefInput.focus();
                }
            });
            window.Studio.addPaletteCommand({
                id: 'agent:stop',
                label: 'Agent: Stop Attack',
                action: stopAgent
            });
        }
    }

})();
