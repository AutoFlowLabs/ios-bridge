// iOS Simulator Device Logs Manager
class DeviceLogsManager {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.logWs = null;
        this.isLogStreaming = false;
        this.logEntries = [];
        this.filteredLogEntries = [];
        this.autoScroll = true;
        this.logCount = 0;
        this.lastLogTime = 0;
        this.logRate = 0;
        this.logsCollapsed = false;
        this.maxDisplayedLogs = 1000;

        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // Get DOM elements
        this.elements = {
            logsSection: document.getElementById('logsSection'),
            logsToggleIcon: document.getElementById('logsToggleIcon'),
            logLevel: document.getElementById('logLevel'),
            logProcess: document.getElementById('logProcess'),
            logSearch: document.getElementById('logSearch'),
            logContainer: document.getElementById('logContainer'),
            logContent: document.getElementById('logContent'),
            logStatus: document.getElementById('logStatus'),
            logCount: document.getElementById('logCount'),
            logRate: document.getElementById('logRate'),
            connectionStatus: document.getElementById('connectionStatus'),
            logStreamBtn: document.getElementById('logStreamBtn'),
            autoScrollBtn: document.getElementById('autoScrollBtn')
        };
    }

    bindEvents() {
        // Bind all event handlers
        if (this.elements.logLevel) {
            this.elements.logLevel.addEventListener('change', () => this.applyLogFilter());
        }
        if (this.elements.logProcess) {
            this.elements.logProcess.addEventListener('change', () => this.applyLogFilter());
        }
        if (this.elements.logSearch) {
            this.elements.logSearch.addEventListener('keyup', () => this.filterDisplayedLogs());
        }
    }

    async initialize() {
        await this.loadLogProcesses();
        this.updateLogStatus();
    }

    toggleLogsSection() {
        if (!this.elements.logsSection || !this.elements.logsToggleIcon) return;

        this.logsCollapsed = !this.logsCollapsed;

        if (this.logsCollapsed) {
            this.elements.logsSection.classList.add('collapsed');
            this.elements.logsToggleIcon.classList.add('collapsed');
            this.elements.logsToggleIcon.textContent = '▶';
            this.showTemporaryStatus('📋 Device logs collapsed');

            // Stop streaming when collapsed
            if (this.isLogStreaming) {
                this.stopLogStream();
            }
        } else {
            this.elements.logsSection.classList.remove('collapsed');
            this.elements.logsToggleIcon.classList.remove('collapsed');
            this.elements.logsToggleIcon.textContent = '▼';
            this.showTemporaryStatus('📋 Device logs expanded');
        }
    }

    async loadLogProcesses() {
        try {
            const response = await fetch(`/api/sessions/${this.sessionId}/logs/processes`);
            const data = await response.json();

            if (!this.elements.logProcess) return;

            this.elements.logProcess.innerHTML = '<option value="">All Processes</option>';

            if (data.success && data.processes) {
                data.processes.forEach(proc => {
                    const option = document.createElement('option');
                    option.value = proc.process;
                    option.textContent = `${proc.process} (${proc.pid})`;
                    this.elements.logProcess.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load log processes:', error);
        }
    }

    toggleLogStream() {
        if (this.isLogStreaming) {
            this.stopLogStream();
        } else {
            this.startLogStream();
        }
    }

    startLogStream() {
        if (this.isLogStreaming || !this.elements.logStreamBtn || !this.elements.logContent) return;

        try {
            // Clear existing logs
            this.logEntries = [];
            this.elements.logContent.innerHTML = '<div class="log-placeholder">🔄 Connecting to log stream...</div>';

            // Create WebSocket connection
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${this.sessionId}/logs`;

            this.logWs = new WebSocket(wsUrl);

            this.logWs.onopen = () => {
                this.isLogStreaming = true;
                this.elements.logStreamBtn.textContent = '⏹️ Stop Stream';
                this.elements.logStreamBtn.classList.add('streaming');
                this.elements.logContent.innerHTML = '';
                this.updateConnectionStatus('Connected');
                this.showTemporaryStatus('📋 Log streaming started');
            };

            this.logWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleLogMessage(data);
            };

            this.logWs.onerror = (error) => {
                console.error('Log WebSocket error:', error);
                this.showTemporaryStatus('❌ Log streaming error');
                this.updateConnectionStatus('Error');
            };

            this.logWs.onclose = () => {
                if (this.isLogStreaming) {
                    this.showTemporaryStatus('📋 Log streaming stopped');
                }
                this.stopLogStream();
            };

        } catch (error) {
            console.error('Failed to start log stream:', error);
            this.showTemporaryStatus('❌ Failed to start log streaming');
        }
    }

    stopLogStream() {
        if (!this.elements.logStreamBtn) return;

        if (this.logWs) {
            this.logWs.close();
            this.logWs = null;
        }

        this.isLogStreaming = false;
        this.elements.logStreamBtn.textContent = '▶️ Start Stream';
        this.elements.logStreamBtn.classList.remove('streaming');
        this.updateConnectionStatus('Disconnected');
    }

    handleLogMessage(data) {
        if (data.type === 'log') {
            // Add to log entries
            this.logEntries.push(data);
            this.logCount++;

            // Update log rate
            const now = Date.now();
            if (this.lastLogTime > 0) {
                const timeDiff = (now - this.lastLogTime) / 1000;
                this.logRate = Math.round(1 / timeDiff * 10) / 10;
            }
            this.lastLogTime = now;

            // Apply current filters
            if (this.shouldShowLogEntry(data)) {
                this.addLogEntryToDisplay(data);
            }

            // Update status
            this.updateLogStatus();

            // Auto-scroll if enabled
            if (this.autoScroll) {
                this.scrollToBottom();
            }
        } else if (data.type === 'clear') {
            this.clearDisplayedLogs();
        }
    }

    shouldShowLogEntry(logData) {
        if (!this.elements.logLevel || !this.elements.logProcess || !this.elements.logSearch) {
            return true;
        }

        const levelFilter = this.elements.logLevel.value;
        const processFilter = this.elements.logProcess.value;
        const searchFilter = this.elements.logSearch.value.toLowerCase();

        // Level filter
        if (levelFilter !== 'all' && logData.level !== levelFilter) {
            return false;
        }

        // Process filter
        if (processFilter && logData.process !== processFilter) {
            return false;
        }

        // Search filter
        if (searchFilter && !logData.message.toLowerCase().includes(searchFilter)) {
            return false;
        }

        return true;
    }

    addLogEntryToDisplay(logData) {
        if (!this.elements.logContent) return;

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${logData.level}`;

        const timestamp = document.createElement('span');
        timestamp.className = 'log-timestamp';
        timestamp.textContent = logData.timestamp;

        const process = document.createElement('span');
        process.className = 'log-process';
        process.textContent = `${logData.process}${logData.pid ? `[${logData.pid}]` : ''}`;

        const message = document.createElement('span');
        message.className = 'log-message';
        message.textContent = logData.message;

        logEntry.appendChild(timestamp);
        logEntry.appendChild(document.createTextNode(' '));
        logEntry.appendChild(process);
        logEntry.appendChild(message);

        this.elements.logContent.appendChild(logEntry);

        // Limit displayed logs to prevent memory issues
        if (this.elements.logContent.children.length > this.maxDisplayedLogs) {
            this.elements.logContent.removeChild(this.elements.logContent.firstChild);
        }
    }

    applyLogFilter() {
        if (!this.elements.logContent) return;

        // Rebuild the displayed logs with current filters
        this.elements.logContent.innerHTML = '';

        this.filteredLogEntries = this.logEntries.filter(logData =>
            this.shouldShowLogEntry(logData)
        );

        this.filteredLogEntries.forEach(logData => {
            this.addLogEntryToDisplay(logData);
        });

        if (this.autoScroll) {
            this.scrollToBottom();
        }

        this.updateLogStatus();
    }

    filterDisplayedLogs() {
        this.applyLogFilter();
    }

    async clearLogs() {
        try {
            console.log('Clearing logs for session:', this.sessionId);

            const response = await fetch(`/api/sessions/${this.sessionId}/logs/clear`, {
                method: 'POST'
            });

            console.log('Clear logs response status:', response.status);
            const data = await response.json();
            console.log('Clear logs response data:', data);

            if (data.success) {
                this.clearDisplayedLogs();
                this.showTemporaryStatus('📋 Device logs cleared');
                console.log('✅ Logs cleared successfully');
            } else {
                this.showTemporaryStatus('❌ Failed to clear logs');
                console.error('Failed to clear logs:', data.message);
            }
        } catch (error) {
            console.error('Failed to clear logs:', error);
            this.showTemporaryStatus('❌ Error clearing logs');
        }
    }
    clearDisplayedLogs() {
        console.log('clearDisplayedLogs called');

        if (!this.elements.logContent) {
            console.error('logContent element not found');
            return;
        }

        // Clear the arrays first
        this.logEntries = [];
        this.filteredLogEntries = [];
        this.logCount = 0;
        this.logRate = 0;
        this.lastLogTime = 0;

        // Clear the display
        this.elements.logContent.innerHTML = '<div class="log-placeholder">📋 Logs cleared</div>';

        // Update the status
        this.updateLogStatus();

        console.log('✅ Display cleared, logEntries length:', this.logEntries.length);
    }

    scrollToBottom() {
        if (!this.elements.logContent) return;

        this.elements.logContent.scrollTop = this.elements.logContent.scrollHeight;
    }

    toggleAutoScroll() {
        if (!this.elements.autoScrollBtn) return;

        this.autoScroll = !this.autoScroll;

        if (this.autoScroll) {
            this.elements.autoScrollBtn.textContent = '📌 Auto-scroll';
            this.elements.autoScrollBtn.classList.remove('btn-secondary');
            this.elements.autoScrollBtn.classList.add('btn-primary');
            this.scrollToBottom();
        } else {
            this.elements.autoScrollBtn.textContent = '📌 Manual';
            this.elements.autoScrollBtn.classList.remove('btn-primary');
            this.elements.autoScrollBtn.classList.add('btn-secondary');
        }
    }

    exportLogs() {
        if (this.logEntries.length === 0) {
            this.showTemporaryStatus('📋 No logs to export');
            return;
        }

        // Create log text
        const logText = this.logEntries.map(entry =>
            `${entry.timestamp} ${entry.process}${entry.pid ? `[${entry.pid}]` : ''} ${entry.level.toUpperCase()}: ${entry.message}`
        ).join('\n');

        // Create and trigger download
        const blob = new Blob([logText], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `ios_simulator_logs_${this.sessionId.substring(0, 8)}_${new Date().getTime()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        this.showTemporaryStatus(`📋 Exported ${this.logEntries.length} log entries`);
    }

    updateLogStatus() {
        console.log('updateLogStatus called, logCount:', this.logCount);

        if (!this.elements.logCount || !this.elements.logRate) {
            console.error('Status elements not found');
            return;
        }

        this.elements.logCount.textContent = `${this.logCount} logs`;
        this.elements.logRate.textContent = `${this.logRate} logs/sec`;

        console.log('Status updated - Count:', this.elements.logCount.textContent, 'Rate:', this.elements.logRate.textContent);
    }

    updateConnectionStatus(status) {
        if (!this.elements.connectionStatus) return;

        this.elements.connectionStatus.textContent = status;

        if (status === 'Connected') {
            this.elements.connectionStatus.style.color = '#28a745';
        } else if (status === 'Error') {
            this.elements.connectionStatus.style.color = '#dc3545';
        } else {
            this.elements.connectionStatus.style.color = '#6c757d';
        }
    }

    // Helper method to show temporary status (should be provided by parent)
    showTemporaryStatus(message) {
        // This should be implemented by the parent application
        if (window.showTemporaryStatus) {
            window.showTemporaryStatus(message);
        } else {
            console.log('Status:', message);
        }
    }

    // Cleanup method
    cleanup() {
        if (this.logWs) {
            this.logWs.close();
            this.logWs = null;
        }
        this.isLogStreaming = false;
    }

    // Keyboard shortcuts handler
    handleKeyboardShortcut(key) {
        switch (key) {
            case 'g':
                this.toggleLogsSection();
                return true;
            case 'Escape':
                if (this.isLogStreaming) {
                    this.stopLogStream();
                    return true;
                }
                break;
        }
        return false;
    }
}

// Global functions for HTML onclick handlers
function toggleLogsSection() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.toggleLogsSection();
    } else {
        console.error('deviceLogsManager not available for toggleLogsSection');
    }
}

function applyLogFilter() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.applyLogFilter();
    }
}

function filterDisplayedLogs() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.filterDisplayedLogs();
    }
}

function clearLogs() {
    console.log('Global clearLogs called');
    console.log('deviceLogsManager exists:', !!window.deviceLogsManager);
    
    if (window.deviceLogsManager) {
        console.log('Calling deviceLogsManager.clearLogs()');
        window.deviceLogsManager.clearLogs();
    } else {
        console.error('deviceLogsManager not available');
        showTemporaryStatus('❌ Log manager not available');
    }
}

function exportLogs() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.exportLogs();
    }
}

function scrollToBottom() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.scrollToBottom();
    }
}

function toggleLogStream() {
    console.log('toggleLogStream called');
    console.log('deviceLogsManager exists:', !!window.deviceLogsManager);

    if (window.deviceLogsManager) {
        console.log('Current streaming state:', window.deviceLogsManager.isLogStreaming);
        window.deviceLogsManager.toggleLogStream();
    } else {
        console.error('deviceLogsManager not initialized');
        showTemporaryStatus('❌ Log manager not initialized - trying to reinitialize...');

        // Try to reinitialize
        initLogViewer();
    }
}
function toggleAutoScroll() {
    if (window.deviceLogsManager) {
        window.deviceLogsManager.toggleAutoScroll();
    }
}

function testWebSocketConnection() {
    console.log('Testing WebSocket connection to logs endpoint');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${SESSION_ID}/logs`;

    console.log('WebSocket URL:', wsUrl);

    const testWs = new WebSocket(wsUrl);

    testWs.onopen = () => {
        console.log('✅ WebSocket connection successful');
        showTemporaryStatus('✅ WebSocket connection successful');
        testWs.close();
    };

    testWs.onerror = (error) => {
        console.error('❌ WebSocket connection failed:', error);
        showTemporaryStatus('❌ WebSocket connection failed');
    };

    testWs.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
    };

    window.toggleLogStream = toggleLogStream;
    window.toggleLogsSection = toggleLogsSection;
    window.applyLogFilter = applyLogFilter;
    window.filterDisplayedLogs = filterDisplayedLogs;
    window.clearLogs = clearLogs;
    window.exportLogs = exportLogs;
    window.scrollToBottom = scrollToBottom;
    window.toggleAutoScroll = toggleAutoScroll; clearLogs
    window.testWebSocketConnection = testWebSocketConnection;

}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeviceLogsManager;
}