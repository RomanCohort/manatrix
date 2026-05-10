/**
 * Manatrix - Professional Frontend Application
 *
 * Modern UI with professional design system, keyboard shortcuts,
 * localStorage persistence, and real-time updates.
 */

// Wait for UI components to load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// ============== State ==============
const state = {
    modelLoaded: false,
    llmConfigured: false,
    generating: false,
    lastFeatures: null
};

// ============== DOM Elements ==============
const els = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebarToggle'),
    themeToggle: document.getElementById('themeToggle'),
    themeIcon: document.getElementById('themeIcon'),

    // Header
    status: document.getElementById('status'),
    shortcutsBtn: document.getElementById('shortcutsBtn'),
    shortcutsModal: document.getElementById('shortcutsModal'),
    closeShortcuts: document.getElementById('closeShortcuts'),

    // Forms
    apiKey: document.getElementById('apiKey'),
    apiBase: document.getElementById('apiBase'),
    configureLLM: document.getElementById('configureLLM'),
    targetInfo: document.getElementById('targetInfo'),
    useLLM: document.getElementById('useLLM'),
    parallelExtract: document.getElementById('parallelExtract'),
    extractStages: document.getElementById('extractStages'),
    genMethod: document.getElementById('genMethod'),
    methodDesc: document.getElementById('methodDesc'),
    nSamples: document.getElementById('nSamples'),
    temperature: document.getElementById('temperature'),
    topK: document.getElementById('topK'),
    topP: document.getElementById('topP'),
    tempSchedule: document.getElementById('tempSchedule'),
    generateBtn: document.getElementById('generateBtn'),

    // Output
    extractedFeatures: document.getElementById('extractedFeatures'),
    passwordResults: document.getElementById('passwordResults'),
    passwordCount: document.getElementById('passwordCount'),
    extractTime: document.getElementById('extractTime'),
    genTime: document.getElementById('genTime'),
    cacheHitRate: document.getElementById('cacheHitRate'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
};

// ============== API Client ==============
const api = {
    async get(path) {
        const res = await fetch(path);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        return res.json();
    },

    async post(path, body) {
        const res = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const detail = await res.text();
            throw new Error(detail);
        }
        return res.json();
    }
};

// ============== Initialize ==============
function initApp() {
    // Load saved preferences
    loadPreferences();

    // Setup sidebar toggle
    setupSidebar();

    // Setup theme toggle
    setupThemeToggle();

    // Setup collapsible sections
    setupCollapsibleSections();

    // Setup keyboard shortcuts
    setupKeyboardShortcuts();

    // Setup shortcuts modal
    setupShortcutsModal();

    // Setup method description
    setupMethodDescription();

    // Setup LLM configuration
    setupLLMConfig();

    // Setup generate button
    setupGenerate();

    // Check initial status
    checkStatus();

    // Periodic status check
    setInterval(checkStatus, 30000);
}

// ============== Preferences ==============
function loadPreferences() {
    // Restore API Base
    const savedApiBase = UI.storageGet('api_base');
    if (savedApiBase) {
        els.apiBase.value = savedApiBase;
    }

    // Restore generation settings
    const savedGen = UI.storageGet('gen_settings');
    if (savedGen) {
        if (savedGen.nSamples) els.nSamples.value = savedGen.nSamples;
        if (savedGen.temperature) els.temperature.value = savedGen.temperature;
        if (savedGen.topK !== undefined) els.topK.value = savedGen.topK;
        if (savedGen.topP) els.topP.value = savedGen.topP;
        if (savedGen.tempSchedule) els.tempSchedule.value = savedGen.tempSchedule;
        if (savedGen.genMethod) els.genMethod.value = savedGen.genMethod;
    }

    // Apply theme icon
    updateThemeIcon();
}

function savePreferences() {
    UI.storageSet('api_base', els.apiBase.value);
    UI.storageSet('gen_settings', {
        nSamples: els.nSamples.value,
        temperature: els.temperature.value,
        topK: els.topK.value,
        topP: els.topP.value,
        tempSchedule: els.tempSchedule.value,
        genMethod: els.genMethod.value,
    });
}

// ============== Sidebar ==============
function setupSidebar() {
    els.sidebarToggle?.addEventListener('click', () => {
        els.sidebar?.classList.toggle('collapsed');
    });
}

// ============== Theme ==============
function setupThemeToggle() {
    els.themeToggle?.addEventListener('click', () => {
        UI.theme.toggle();
        updateThemeIcon();
    });
}

function updateThemeIcon() {
    if (els.themeIcon) {
        els.themeIcon.innerHTML = UI.theme.get() === 'dark' ? UI.Icons.moon : UI.Icons.sun;
    }
}

// ============== Collapsible Sections ==============
function setupCollapsibleSections() {
    document.querySelectorAll('.collapsible .section-header').forEach(header => {
        header.addEventListener('click', () => {
            const section = header.closest('.collapsible');
            section.classList.toggle('expanded');
        });
    });
}

// ============== Keyboard Shortcuts ==============
function setupKeyboardShortcuts() {
    // Ctrl+K - Focus search (if exists)
    UI.shortcuts.register('mod+k', () => {
        els.targetInfo?.focus();
    });

    // Ctrl+B - Toggle sidebar
    UI.shortcuts.register('mod+b', () => {
        els.sidebar?.classList.toggle('collapsed');
    });

    // Ctrl+Enter - Generate
    UI.shortcuts.register('mod+enter', () => {
        if (!state.generating) {
            els.generateBtn?.click();
        }
    });

    // Ctrl+/ - Toggle shortcuts modal
    UI.shortcuts.register('mod+/', () => {
        toggleShortcutsModal();
    });

    // Escape - Close modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeShortcutsModal();
        }
    });
}

// ============== Shortcuts Modal ==============
function setupShortcutsModal() {
    els.shortcutsBtn?.addEventListener('click', () => {
        toggleShortcutsModal();
    });

    els.closeShortcuts?.addEventListener('click', () => {
        closeShortcutsModal();
    });

    els.shortcutsModal?.addEventListener('click', (e) => {
        if (e.target === els.shortcutsModal) {
            closeShortcutsModal();
        }
    });
}

function toggleShortcutsModal() {
    els.shortcutsModal?.classList.toggle('active');
}

function closeShortcutsModal() {
    els.shortcutsModal?.classList.remove('active');
}

// ============== Method Description ==============
function setupMethodDescription() {
    const descriptions = {
        sampling: '标准采样，支持温度和 top-k/top-p 调节',
        beam: 'Beam Search - 搜索多条路径选最优',
        diverse_beam: '多组 Beam Search，加入多样性惩罚',
        typical: '基于信息熵的典型采样，输出更连贯',
        contrastive: '对比搜索，惩罚重复内容'
    };

    els.genMethod.addEventListener('change', () => {
        els.methodDesc.textContent = descriptions[els.genMethod.value] || '';
        savePreferences();
    });

    // Show initial description
    els.genMethod.dispatchEvent(new Event('change'));
}

// ============== LLM Configuration ==============
function setupLLMConfig() {
    els.configureLLM.addEventListener('click', async () => {
        const apiKey = els.apiKey.value.trim();
        const apiBase = els.apiBase.value.trim();

        if (!apiKey) {
            UI.toast.warning('请输入 API Key', '需要 API Key 才能配置 LLM');
            return;
        }

        try {
            showLoading('配置 LLM...');
            await api.post(`/api/configure_llm?api_key=${encodeURIComponent(apiKey)}&api_base=${encodeURIComponent(apiBase)}`);
            state.llmConfigured = true;
            savePreferences();
            UI.toast.success('配置成功', 'LLM 已配置完成');
        } catch (e) {
            UI.toast.error('配置失败', e.message);
        } finally {
            hideLoading();
        }
    });
}

// ============== Generate ==============
function setupGenerate() {
    els.generateBtn.addEventListener('click', generate);
}

async function generate() {
    if (state.generating) return;

    const targetInfo = els.targetInfo.value.trim();
    if (!targetInfo) {
        UI.toast.warning('请输入目标信息', '需要提供目标信息才能生成密码');
        els.targetInfo.focus();
        return;
    }

    state.generating = true;
    els.generateBtn.disabled = true;

    try {
        // Step 1: Load model if needed
        if (!state.modelLoaded) {
            showLoading('加载模型...');
            try {
                const result = await api.post('/api/load_model');
                state.modelLoaded = true;
                UI.toast.success('模型已加载', `${result.parameters.toLocaleString()} 参数`);
            } catch (e) {
                UI.toast.error('模型加载失败', e.message);
                return;
            }
        }

        // Step 2: Generate
        showLoading('生成密码中...');
        savePreferences();

        const requestBody = {
            target_info: {
                raw_text: targetInfo,
                use_llm_extraction: state.llmConfigured && els.useLLM.checked,
                extraction_stages: parseInt(els.extractStages.value),
                parallel_extraction: els.parallelExtract.checked
            },
            generation: {
                method: els.genMethod.value,
                n_samples: parseInt(els.nSamples.value),
                temperature: parseFloat(els.temperature.value),
                temperature_schedule: els.tempSchedule.value,
                top_k: parseInt(els.topK.value),
                top_p: parseFloat(els.topP.value),
                beam_width: 5,
                diversity_penalty: 0.5,
                typical_mass: 0.9,
                contrastive_alpha: 0.5
            }
        };

        const result = await api.post('/api/generate', requestBody);

        // Render results
        renderFeatures(result.extracted_features);
        renderPasswords(result.passwords);

        // Update stats
        els.extractTime.textContent = result.extraction_time.toFixed(2) + 's';
        els.genTime.textContent = result.generation_time.toFixed(2) + 's';

        // Get cache stats
        try {
            const status = await api.get('/api/status');
            els.cacheHitRate.textContent = (status.cache_stats.hit_rate * 100).toFixed(1) + '%';
        } catch (e) {}

        UI.toast.success('生成完成', `已生成 ${result.passwords.length} 个密码`);

    } catch (e) {
        UI.toast.error('生成失败', e.message);
        console.error(e);
    } finally {
        state.generating = false;
        els.generateBtn.disabled = false;
        hideLoading();
    }
}

// ============== Status ==============
async function checkStatus() {
    try {
        const data = await api.get('/api/status');
        updateStatus(true, data.device, data.model_loaded);
        state.modelLoaded = data.model_loaded;
    } catch (e) {
        updateStatus(false);
    }
}

function updateStatus(connected, device = '', modelLoaded = false) {
    const statusEl = els.status;
    if (connected) {
        statusEl.className = 'status-badge connected';
        statusEl.innerHTML = `
            <span class="status-dot"></span>
            <span class="status-text">${device} | 模型${modelLoaded ? '已加载' : '未加载'}</span>
        `;
    } else {
        statusEl.className = 'status-badge error';
        statusEl.innerHTML = `
            <span class="status-dot"></span>
            <span class="status-text">连接失败</span>
        `;
    }
}

// ============== Loading ==============
function showLoading(text = '处理中...') {
    els.loadingText.textContent = text;
    els.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    els.loadingOverlay.classList.add('hidden');
}

// ============== Feature Display ==============
function renderFeatures(features) {
    if (!features || Object.keys(features).length === 0) {
        els.extractedFeatures.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">${UI.Icons.info}</span>
                <p class="empty-text">无提取结果</p>
            </div>
        `;
        return;
    }

    const fields = [
        { key: 'full_name', label: '全名' },
        { key: 'first_name', label: '名' },
        { key: 'last_name', label: '姓' },
        { key: 'nickname', label: '昵称' },
        { key: 'birthday', label: '生日' },
        { key: 'phone', label: '电话' },
        { key: 'email_prefix', label: '邮箱前缀' },
        { key: 'city', label: '城市' },
        { key: 'country', label: '国家' },
    ];

    const listFields = [
        { key: 'hobbies', label: '兴趣爱好' },
        { key: 'favorite_words', label: '喜爱词汇' },
        { key: 'favorite_numbers', label: '喜爱数字' },
        { key: 'pet_names', label: '宠物名' },
        { key: 'keywords', label: '关键词' },
    ];

    let html = '';

    // String fields
    for (const field of fields) {
        const value = features[field.key] || '';
        const hasValue = value.length > 0;
        html += `
            <div class="feature-tag ${hasValue ? 'has-value' : ''}">
                <span class="feature-label">${field.label}</span>
                <span class="feature-value ${!hasValue ? 'empty' : ''}">${hasValue ? escapeHtml(value) : '-'}</span>
            </div>
        `;
    }

    // List fields
    for (const field of listFields) {
        const values = features[field.key] || [];
        const hasValue = values.length > 0;
        html += `
            <div class="feature-tag ${hasValue ? 'has-value' : ''}" style="grid-column: span 2;">
                <span class="feature-label">${field.label}</span>
                <span class="feature-value ${!hasValue ? 'empty' : ''}">
                    ${hasValue ? values.map(v => `<span class="feature-list-item">${escapeHtml(String(v))}</span>`).join(' ') : '-'}
                </span>
            </div>
        `;
    }

    els.extractedFeatures.innerHTML = html;
}

// ============== Password Display ==============
function renderPasswords(passwords) {
    if (!passwords || passwords.length === 0) {
        els.passwordResults.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">${UI.Icons.lock}</span>
                <p class="empty-text">无生成结果</p>
            </div>
        `;
        els.passwordCount.textContent = '';
        return;
    }

    els.passwordCount.textContent = passwords.length;

    let html = '';
    for (let i = 0; i < passwords.length; i++) {
        const p = passwords[i];
        const scoreText = p.score != null ? p.score.toFixed(3) : '';
        const methodText = p.method || '';
        const strength = UI.getPasswordStrength(p.password);

        html += `
            <div class="password-card" onclick="copyPassword(this, '${escapeJs(p.password)}')" title="点击复制">
                <div class="pwd-header">
                    <span class="pwd-text">${escapeHtml(p.password)}</span>
                    <button class="pwd-copy" onclick="event.stopPropagation(); copyPassword(this.parentElement.parentElement, '${escapeJs(p.password)}')">
                        ${UI.Icons.copy}
                    </button>
                </div>
                <div class="pwd-info">
                    ${methodText ? `<span class="pwd-method">${methodText}</span>` : ''}
                    ${scoreText ? `<span class="pwd-score" style="color: ${strength.color}">${scoreText}</span>` : ''}
                </div>
                <div class="pwd-strength">
                    <div class="strength-bar" style="width: ${strength.percent}%; background: ${strength.color}"></div>
                </div>
            </div>
        `;
    }

    els.passwordResults.innerHTML = html;
}

function copyPassword(el, password) {
    UI.copyToClipboard(password);
    el.classList.add('copied');
    setTimeout(() => el.classList.remove('copied'), 800);
}

// ============== Utility ==============
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escapeJs(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}