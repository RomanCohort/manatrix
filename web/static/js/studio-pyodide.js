/**
 * Manatrix Studio - Pyodide Module
 *
 * Browser-based Python execution using Pyodide (WebAssembly Python)
 * Enables parallel Python execution without blocking the terminal
 */

// ==========================================================================
// Pyodide State
// ==========================================================================

// Pyodide instance (loaded once, reused)
let pyodide = null;
let pyodideLoading = false;
let pyodideReady = false;
let pyodideLoadPromise = null;

// Python namespace for variable persistence
const pyodideNamespace = {};

// ==========================================================================
// Pyodide Initialization
// ==========================================================================

async function initPyodide() {
    if (pyodideReady) return pyodide;
    if (pyodideLoading) return pyodideLoadPromise;

    pyodideLoading = true;

    pyodideLoadPromise = (async () => {
        try {
            state.terminal.write('\r\n\x1b[33m[*] Loading Python runtime (Pyodide ~10MB)...\x1b[0m\r\n');

            // Load Pyodide from CDN
            await loadScript('https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js');

            pyodide = await loadPyodide({
                indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
            });

            // Setup stdout/stderr capture
            pyodide.runPython(`
import sys
from io import StringIO

class OutputCapture:
    def __init__(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    def get_stdout(self):
        val = self.stdout.getvalue()
        self.stdout = StringIO()
        return val

    def get_stderr(self):
        val = self.stderr.getvalue()
        self.stderr = StringIO()
        return val

    def write_stdout(self, s):
        self.stdout.write(s)

    def write_stderr(self, s):
        self.stderr.write(s)

_output_capture = OutputCapture()
sys.stdout = _output_capture
sys.stderr = _output_capture
            `);

            // Load common packages
            state.terminal.write('\x1b[90m[*] Loading common packages...\x1b[0m\r\n');
            await pyodide.loadPackage(['numpy', 'matplotlib', 'pandas']);

            // Setup matplotlib for browser
            pyodide.runPython(`
import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def _save_plot_to_base64():
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def show_plot():
    """Display the current matplotlib figure in the plots panel."""
    import js
    b64 = _save_plot_to_base64()
    img_url = f"data:image/png;base64,{b64}"
    # Call JS function to display
    js.window._displayPyodidePlot(img_url)
    plt.close()
            `);

            // Expose display function to JS
            pyodide.globals.set('_displayPyodidePlot', (url) => {
                displayPyodidePlot(url);
            });

            pyodideReady = true;
            pyodideLoading = false;
            state.terminal.write('\x1b[32m[+] Python runtime ready!\x1b[0m\r\n');
            state.terminal.write('\x1b[90m    Packages: numpy, matplotlib, pandas\x1b[0m\r\n');
            state.terminal.write('\x1b[90m    Use plt.show() or show_plot() to display figures\x1b[0m\r\n');
            state.terminal.write('\x1b[90m$ \x1b[0m');

            return pyodide;
        } catch (e) {
            pyodideLoading = false;
            state.terminal.write(`\x1b[31m[-] Failed to load Python: ${e}\x1b[0m\r\n`);
            throw e;
        }
    })();

    return pyodideLoadPromise;
}

// ==========================================================================
// Python Code Execution
// ==========================================================================

async function runPyodideCode(code) {
    if (!pyodideReady) {
        await initPyodide();
    }

    try {
        // Reset output capture
        pyodide.runPython('_output_capture.stdout = _output_capture.stderr = __import__("io").StringIO()');

        // Run the code
        const result = await pyodide.runPythonAsync(code);

        // Get captured output
        const stdout = pyodide.runPython('_output_capture.get_stdout()');
        const stderr = pyodide.runPython('_output_capture.get_stderr()');

        // Display output
        if (stdout) {
            state.terminal.write(stdout.replace(/\n/g, '\r\n'));
        }
        if (stderr) {
            state.terminal.write('\x1b[31m' + stderr.replace(/\n/g, '\r\n\x1b[31m') + '\x1b[0m');
        }

        // Display result if not None
        if (result !== undefined && result !== null) {
            const resultStr = result.toString();
            if (resultStr && resultStr !== 'None') {
                state.terminal.write('\x1b[36m' + resultStr.replace(/\n/g, '\r\n') + '\x1b[0m\r\n');
            }
        }

        // Update variables panel
        refreshPyodideVariables();

    } catch (e) {
        const errorMsg = e.message || e.toString();
        state.terminal.write('\x1b[31m' + errorMsg.replace(/\n/g, '\r\n\x1b[31m') + '\x1b[0m\r\n');
    }

    state.terminal.write('\x1b[90m$ \x1b[0m');
}

// ==========================================================================
// Variable Inspection
// ==========================================================================

function refreshPyodideVariables() {
    if (!pyodideReady) return;

    try {
        const vars = pyodide.runPython(`
import json
{str(k): str(type(v).__name__) + ': ' + str(v)[:50]
 for k, v in globals().items()
 if not k.startswith('_') and not callable(v) and not isinstance(v, type)}
        `);

        const varsObj = vars.toJs();
        const panel = document.getElementById('variablesPanel');
        if (panel && varsObj.size > 0) {
            let html = '';
            varsObj.forEach((value, key) => {
                html += `<div class="env-item">
                    <span class="env-item-name">${escapeHtml(key)}</span>
                    <span class="env-item-value">${escapeHtml(String(value))}</span>
                </div>`;
            });
            panel.innerHTML = html || '<div class="env-item" style="color:var(--studio-text-muted);font-style:italic;">No variables defined</div>';
        }
    } catch (e) {
        // Ignore variable inspection errors
    }
}

// ==========================================================================
// Plot Display
// ==========================================================================

function displayPyodidePlot(dataUrl) {
    addChart(dataUrl);
}

// ==========================================================================
// Package Management
// ==========================================================================

async function loadPyodidePackage(packageName) {
    if (!pyodideReady) {
        await initPyodide();
    }

    try {
        state.terminal.write(`\x1b[33m[*] Loading package: ${packageName}...\x1b[0m\r\n`);
        await pyodide.loadPackage(packageName);
        state.terminal.write(`\x1b[32m[+] Package loaded: ${packageName}\x1b[0m\r\n`);
    } catch (e) {
        state.terminal.write(`\x1b[31m[-] Failed to load package: ${e}\x1b[0m\r\n`);
    }
    state.terminal.write('\x1b[90m$ \x1b[0m');
}

// ==========================================================================
// Autocomplete Support
// ==========================================================================

function getPyodideCompletions(prefix) {
    if (!pyodideReady || !prefix) return [];

    try {
        const completions = pyodide.runPython(`
import rlcompleter
c = rlcompleter.Completer()
[c.complete('${prefix}', i)[0] for i in range(50) if c.complete('${prefix}', i)]
        `);
        return completions.toJs();
    } catch (e) {
        return [];
    }
}

// ==========================================================================
// Reset Python Environment
// ==========================================================================

async function resetPyodideEnvironment() {
    if (!pyodideReady) return;

    pyodide.runPython(`
import sys
for name in list(globals().keys()):
    if not name.startswith('_') and name not in ['sys', '__builtins__']:
        del globals()[name]
    `);

    state.terminal.write('\x1b[32m[+] Python environment reset\x1b[0m\r\n');
    refreshPyodideVariables();
}

// ==========================================================================
// Exports
// ==========================================================================

window.runPyodideCode = runPyodideCode;
window.loadPyodidePackage = loadPyodidePackage;
window.resetPyodideEnvironment = resetPyodideEnvironment;
window.getPyodideCompletions = getPyodideCompletions;
window.initPyodide = initPyodide;
