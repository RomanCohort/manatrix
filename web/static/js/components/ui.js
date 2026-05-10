/**
 * UI Components Library
 *
 * Reusable UI components for the Manatrix frontend.
 * No external dependencies - pure vanilla JavaScript.
 */

// ============== Icons ==============
const Icons = {
    // Navigation
    home: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    shield: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    target: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    key: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
    terminal: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    users: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    brain: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44A2.5 2.5 0 0 1 2 17.5a2.5 2.5 0 0 1 1.03-2.02A2.5 2.5 0 0 1 4.5 11.5h.01a2.5 2.5 0 0 1 .44-4.96A2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44A2.5 2.5 0 0 0 22 17.5a2.5 2.5 0 0 0-1.03-2.02A2.5 2.5 0 0 0 19.5 11.5h-.01a2.5 2.5 0 0 0-.44-4.96A2.5 2.5 0 0 0 14.5 2z"/></svg>',
    graph: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><line x1="9.5" y1="10.5" x2="5.5" y2="7.5"/><line x1="14.5" y1="10.5" x2="18.5" y2="7.5"/><line x1="9.5" y1="13.5" x2="5.5" y2="16.5"/><line x1="14.5" y1="13.5" x2="18.5" y2="16.5"/></svg>',
    book: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    file: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    settings: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    search: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    sun: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
    moon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    bell: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
    menu: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
    x: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    check: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
    alert: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    copy: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    zap: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    globe: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    lock: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    download: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    play: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    plus: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    bug: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="8" y="6" width="8" height="14" rx="4"/><path d="M12 2v4"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>',
};


// ============== Toast System ==============
class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
        this.toasts = [];
    }

    show(type, title, message, duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${Icons[type] || Icons.info}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                ${message ? `<div class="toast-message">${message}</div>` : ''}
            </div>
            <div class="toast-close" onclick="this.parentElement.remove()">${Icons.x}</div>
        `;

        this.container.appendChild(toast);
        this.toasts.push(toast);

        if (duration > 0) {
            setTimeout(() => this.dismiss(toast), duration);
        }

        return toast;
    }

    dismiss(toast) {
        if (!toast || !toast.parentElement) return;
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 200);
    }

    success(title, message) { return this.show('success', title, message); }
    error(title, message) { return this.show('error', title, message); }
    warning(title, message) { return this.show('warning', title, message); }
    info(title, message) { return this.show('info', title, message); }
}

// Global toast instance
const toast = new ToastManager();


// ============== Modal System ==============
class Modal {
    constructor(options = {}) {
        this.options = {
            title: '',
            content: '',
            size: 'md', // sm, md, lg, xl
            closable: true,
            onClose: null,
            ...options
        };

        this.backdrop = document.createElement('div');
        this.backdrop.className = 'modal-backdrop';

        this.modal = document.createElement('div');
        this.modal.className = `modal modal-${this.options.size}`;

        this.render();
        this.bindEvents();
    }

    render() {
        this.modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${this.options.title}</h3>
                ${this.options.closable ? `<div class="modal-close">${Icons.x}</div>` : ''}
            </div>
            <div class="modal-body">${this.options.content}</div>
        `;

        document.body.appendChild(this.backdrop);
        document.body.appendChild(this.modal);
    }

    bindEvents() {
        this.backdrop.addEventListener('click', () => this.close());
        const closeBtn = this.modal.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) this.close();
        });
    }

    open() {
        this.backdrop.classList.add('active');
        this.modal.classList.add('active');
        return this;
    }

    close() {
        this.backdrop.classList.remove('active');
        this.modal.classList.remove('active');
        if (this.options.onClose) this.options.onClose();
        return this;
    }

    isOpen() {
        return this.modal.classList.contains('active');
    }

    destroy() {
        this.backdrop.remove();
        this.modal.remove();
    }

    static confirm(title, message) {
        return new Promise((resolve) => {
            const modal = new Modal({
                title,
                content: `
                    <p>${message}</p>
                    <div class="modal-footer" style="border:none; background:none; padding:0; margin-top: var(--space-4);">
                        <button class="btn btn-secondary" id="modal-cancel">Cancel</button>
                        <button class="btn btn-primary" id="modal-confirm">Confirm</button>
                    </div>
                `,
                closable: true
            });

            modal.modal.querySelector('#modal-confirm').addEventListener('click', () => {
                modal.destroy();
                resolve(true);
            });

            modal.modal.querySelector('#modal-cancel').addEventListener('click', () => {
                modal.destroy();
                resolve(false);
            });

            modal.open();
        });
    }
}


// ============== Theme Manager ==============
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('pg-theme') || 'dark';
        this.apply();
    }

    apply() {
        document.documentElement.setAttribute('data-theme', this.theme);
        localStorage.setItem('pg-theme', this.theme);
    }

    toggle() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        this.apply();
        return this.theme;
    }

    get() {
        return this.theme;
    }
}

const theme = new ThemeManager();


// ============== Keyboard Shortcuts ==============
class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {};
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Ignore when typing in inputs
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

            const key = this.buildKey(e);
            const handler = this.shortcuts[key];
            if (handler) {
                e.preventDefault();
                handler();
            }
        });
    }

    buildKey(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('mod');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }

    register(key, handler) {
        this.shortcuts[key] = handler;
    }

    unregister(key) {
        delete this.shortcuts[key];
    }
}

const shortcuts = new KeyboardShortcuts();

// Register global shortcuts
shortcuts.register('mod+k', () => {
    const searchInput = document.getElementById('global-search');
    if (searchInput) searchInput.focus();
});

shortcuts.register('mod+/', () => {
    const helpModal = document.getElementById('help-modal');
    if (helpModal) helpModal.classList.toggle('active');
});


// ============== Copy to Clipboard ==============
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            toast.success('Copied', 'Copied to clipboard');
        });
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        toast.success('Copied', 'Copied to clipboard');
    }
}


// ============== Date/Time Formatting ==============
function formatTime(date) {
    if (!(date instanceof Date)) date = new Date(date);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(date) {
    if (!(date instanceof Date)) date = new Date(date);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return `${m}m ${s}s`;
}

function timeAgo(date) {
    if (!(date instanceof Date)) date = new Date(date);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}


// ============== Local Storage Helpers ==============
function storageGet(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(`pg-${key}`);
        return value ? JSON.parse(value) : defaultValue;
    } catch {
        return defaultValue;
    }
}

function storageSet(key, value) {
    try {
        localStorage.setItem(`pg-${key}`, JSON.stringify(value));
    } catch (e) {
        console.warn('LocalStorage write failed:', e);
    }
}

function storageRemove(key) {
    localStorage.removeItem(`pg-${key}`);
}


// ============== Password Strength ==============
function getPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (password.length >= 16) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    if (score <= 2) return { level: 'weak', color: '#ef4444', percent: 25 };
    if (score <= 4) return { level: 'fair', color: '#f59e0b', percent: 50 };
    if (score <= 5) return { level: 'good', color: '#10b981', percent: 75 };
    return { level: 'strong', color: '#059669', percent: 100 };
}


// ============== Severity Helpers ==============
function getSeverityBadge(severity) {
    const colors = {
        critical: 'badge-critical',
        high: 'badge-high',
        medium: 'badge-medium',
        low: 'badge-low',
        info: 'badge-info',
    };
    return `<span class="badge ${colors[severity.toLowerCase()] || 'badge-info'}">${severity.toUpperCase()}</span>`;
}


// ============== DOM Helpers ==============
function $(selector, parent = document) {
    return parent.querySelector(selector);
}

function $$(selector, parent = document) {
    return Array.from(parent.querySelectorAll(selector));
}

function createElement(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'className') el.className = value;
        else if (key === 'innerHTML') el.innerHTML = value;
        else if (key === 'textContent') el.textContent = value;
        else if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), value);
        else el.setAttribute(key, value);
    });
    children.forEach(child => {
        if (typeof child === 'string') el.appendChild(document.createTextNode(child));
        else if (child) el.appendChild(child);
    });
    return el;
}


// ============== API Helper ==============
async function apiFetch(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
    };

    const token = storageGet('auth-token');
    if (token) {
        defaults.headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...defaults, ...options });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// Export for use in other modules
window.UI = {
    Icons,
    toast,
    Modal,
    theme,
    shortcuts,
    copyToClipboard,
    formatTime,
    formatDate,
    formatDuration,
    timeAgo,
    storageGet,
    storageSet,
    storageRemove,
    getPasswordStrength,
    getSeverityBadge,
    $,
    $$,
    createElement,
    apiFetch,
};
