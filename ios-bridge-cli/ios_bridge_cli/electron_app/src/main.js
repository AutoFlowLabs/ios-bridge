// Suppress Electron security warnings in production
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';

const { app, BrowserWindow, ipcMain, screen, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

class IOSBridgeApp {
    constructor() {
        this.mainWindow = null;
        this.config = null;
        this.isQuitting = false;
        
        // Handle command line arguments
        this.parseArgs();
        
        // Set up app event handlers
        this.setupAppHandlers();
        
        // Set up IPC handlers
        this.setupIpcHandlers();
    }
    
    parseArgs() {
        const args = process.argv;
        const configIndex = args.indexOf('--config');
        
        if (configIndex !== -1 && configIndex + 1 < args.length) {
            const configPath = args[configIndex + 1];
            try {
                const configData = fs.readFileSync(configPath, 'utf8');
                this.config = JSON.parse(configData);
                console.log('Loaded config:', this.config);
            } catch (error) {
                console.error('Failed to load config:', error);
                process.exit(1);
            }
        } else {
            console.error('No config file specified');
            process.exit(1);
        }
        
        // Handle command line overrides
        this.handleCommandLineOverrides(args);
    }
    
    handleCommandLineOverrides(args) {
        console.log('🔧 Raw command line args:', args);
        
        // Override session ID if provided (handle both --session-id=value and --session-id value formats)
        let newSessionId = null;
        
        // Check for --session-id=value format
        const sessionIdArg = args.find(arg => arg.startsWith('--session-id='));
        if (sessionIdArg) {
            newSessionId = sessionIdArg.split('=')[1];
            console.log(`🔍 Found --session-id=value format: ${newSessionId}`);
        } else {
            // Check for --session-id value format
            const sessionIndex = args.indexOf('--session-id');
            if (sessionIndex !== -1 && sessionIndex + 1 < args.length) {
                newSessionId = args[sessionIndex + 1];
                console.log(`🔍 Found --session-id value format: ${newSessionId}`);
            }
        }
        
        if (newSessionId) {
            console.log(`🔄 Overriding session ID: ${this.config.sessionId} → ${newSessionId}`);
            this.config.sessionId = newSessionId;
        } else {
            console.log('ℹ️ No --session-id override found');
        }
        
        // Override server host if provided (handle both formats)
        let newHost = args.find(arg => arg.startsWith('--server-host='))?.split('=')[1];
        if (!newHost) {
            const hostIndex = args.indexOf('--server-host');
            if (hostIndex !== -1 && hostIndex + 1 < args.length) {
                newHost = args[hostIndex + 1];
            }
        }
        if (newHost) {
            console.log(`🔄 Overriding server host: ${this.config.serverHost} → ${newHost}`);
            this.config.serverHost = newHost;
        }
        
        // Override server port if provided (handle both formats)
        let newPort = args.find(arg => arg.startsWith('--server-port='))?.split('=')[1];
        if (!newPort) {
            const portIndex = args.indexOf('--server-port');
            if (portIndex !== -1 && portIndex + 1 < args.length) {
                newPort = args[portIndex + 1];
            }
        }
        if (newPort) {
            const portNumber = parseInt(newPort);
            console.log(`🔄 Overriding server port: ${this.config.serverPort} → ${portNumber}`);
            this.config.serverPort = portNumber;
        }
        
        // Override quality if provided (handle both formats)
        let newQuality = args.find(arg => arg.startsWith('--quality='))?.split('=')[1];
        if (!newQuality) {
            const qualityIndex = args.indexOf('--quality');
            if (qualityIndex !== -1 && qualityIndex + 1 < args.length) {
                newQuality = args[qualityIndex + 1];
            }
        }
        if (newQuality) {
            console.log(`🔄 Overriding quality: ${this.config.streaming.quality} → ${newQuality}`);
            this.config.streaming.quality = newQuality;
        }
        
        // Enable fullscreen if provided
        if (args.includes('--fullscreen')) {
            console.log('🔄 Enabling fullscreen mode');
            this.config.fullscreen = true;
        }
        
        // Enable always on top if provided
        if (args.includes('--always-on-top')) {
            console.log('🔄 Enabling always on top');
            this.config.alwaysOnTop = true;
        }
    }
    
    setupAppHandlers() {
        app.whenReady().then(() => {
            this.createWindow();
            
            app.on('activate', () => {
                if (BrowserWindow.getAllWindows().length === 0) {
                    this.createWindow();
                }
            });
        });
        
        app.on('window-all-closed', () => {
            this.isQuitting = true;
            app.quit();
        });
        
        app.on('before-quit', async (event) => {
            if (!this.isQuitting) {
                event.preventDefault(); // Prevent quit until cleanup is done
                this.isQuitting = true;
                
                console.log('🧹 Starting cleanup process...');
                
                // Cleanup recordings before quitting
                if (this.iosBridgeProcess && this.config) {
                    try {
                        const serverUrl = this.getServerUrl();
                        console.log('🎬 Stopping all recordings...');
                        
                        // Give it more time and better error handling
                        const controller = new AbortController();
                        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
                        
                        await fetch(`${serverUrl}/api/sessions/cleanup-recordings`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            signal: controller.signal
                        });
                        
                        clearTimeout(timeoutId);
                        console.log('✅ Recording cleanup completed');
                        
                        // Small delay to ensure cleanup completes
                        await new Promise(resolve => setTimeout(resolve, 500));
                        
                    } catch (error) {
                        console.error('❌ Error during recording cleanup:', error);
                    }
                }
                
                console.log('🧹 Cleanup completed, proceeding with quit...');
                app.quit(); // Now actually quit
            }
        });
        
        // Handle external termination signals
        process.on('SIGTERM', () => {
            this.isQuitting = true;
            app.quit();
            // Force exit after 2 seconds if app.quit() doesn't work
            setTimeout(() => process.exit(0), 2000);
        });
        
        process.on('SIGINT', () => {
            this.isQuitting = true;
            app.quit();
            // Force exit after 2 seconds if app.quit() doesn't work
            setTimeout(() => process.exit(0), 2000);
        });
    }
    
    setupIpcHandlers() {
        ipcMain.handle('get-config', () => {
            return this.config;
        });
        
        ipcMain.handle('quit-app', () => {
            this.isQuitting = true;
            app.quit();
        });
        
        ipcMain.handle('minimize-window', () => {
            if (this.mainWindow) {
                this.mainWindow.minimize();
            }
        });
        
        ipcMain.handle('toggle-fullscreen', () => {
            if (this.mainWindow) {
                const isFullScreen = this.mainWindow.isFullScreen();
                this.mainWindow.setFullScreen(!isFullScreen);
                return !isFullScreen;
            }
            return false;
        });
        
        ipcMain.handle('set-always-on-top', (event, alwaysOnTop) => {
            if (this.mainWindow) {
                this.mainWindow.setAlwaysOnTop(alwaysOnTop);
            }
        });
        
        ipcMain.handle('resize-window', (event, width, height) => {
            if (this.mainWindow) {
                // Validate inputs - ensure they are valid numbers
                if (typeof width !== 'number' || typeof height !== 'number' || 
                    isNaN(width) || isNaN(height) || 
                    width <= 0 || height <= 0) {
                    console.error(`Invalid dimensions received: width=${width}, height=${height}`);
                    return { error: 'invalid_dimensions' }; // Don't attempt to resize with invalid values
                }
                
                // Get available screen dimensions
                const currentDisplay = screen.getDisplayNearestPoint({
                    x: this.mainWindow.getBounds().x, 
                    y: this.mainWindow.getBounds().y
                });
                const { width: workWidth, height: workHeight } = currentDisplay.workAreaSize;
                
                // Visual shell padding (from styles.css .device-shell padding: 10px on each side)
                const shellPadding = 20; // total (left+right or top+bottom)
                const headerHeight = 48;
                const footerHeight = 32;
                
                // Compute scale factor to fit both width and height within work area
                const maxScaleCap = 1.0; // don't upscale beyond 100%
                const availableWidth = Math.max(200, workWidth - 40); // leave margin
                const availableHeight = Math.max(200, workHeight - (headerHeight + footerHeight) - 60);
                const scaleByWidth = availableWidth / (width + shellPadding);
                const scaleByHeight = availableHeight / (height + shellPadding);
                const scaleFactor = Math.max(0.1, Math.min(maxScaleCap, scaleByWidth, scaleByHeight));
                
                // Apply the scale
                const scaledContentWidth = Math.round(width * scaleFactor);
                const scaledContentHeight = Math.round(height * scaleFactor);
                
                // Total window size includes header/footer and shell padding
                const windowWidth = scaledContentWidth + shellPadding; // add horizontal shell padding
                const windowHeight = scaledContentHeight + shellPadding + headerHeight + footerHeight;
                
                // Window resized
                
                // Update min size constraints to allow shrinking when orientation or stream size changes
                try {
                    this.mainWindow.setMinimumSize(windowWidth, windowHeight);
                } catch (e) {
                    console.warn('Failed to update minimum window size:', e?.message || e);
                }

                this.mainWindow.setSize(windowWidth, windowHeight);
                this.mainWindow.center(); // Center the window after resizing
                
                return {
                    contentWidth: scaledContentWidth,
                    contentHeight: scaledContentHeight,
                    scaleFactor
                };
            }
            return { error: 'no_window' };
        });
    }
    
    createWindow() {
        const primaryDisplay = screen.getPrimaryDisplay();
        const { width: workWidth, height: workHeight } = primaryDisplay.workAreaSize;
        
        // Get dimensions from config session info
        const sessionInfo = this.config?.sessionInfo || {};
        // Prefer actual stream pixel dimensions for sizing
        let baseWidth = sessionInfo.stream_width || sessionInfo.device_width || 390;
        let baseHeight = sessionInfo.stream_height || sessionInfo.device_height || 844;
        
        // Validate dimensions - ensure they're reasonable (allow smaller desktop-scaled dimensions)
        if (baseWidth < 200 || baseWidth > 4000) baseWidth = sessionInfo.device_width || 390;
        if (baseHeight < 400 || baseHeight > 8000) baseHeight = sessionInfo.device_height || 844;
        
        // Visual shell padding and chrome sizes
        const headerHeight = 48;  // Header height from CSS
        const footerHeight = 32;  // Footer height from CSS
        const shellPadding = 20;  // 10px on all sides in styles.css
        
        // Apply scaling factor to fit within monitor size (consider both width and height)
        const maxScaleCap = 1.0; // allow up to 100% of base size but no upscaling
        const availableWidth = Math.max(200, workWidth - 40); // leave some margin
        const availableHeight = Math.max(200, workHeight - (headerHeight + footerHeight) - 60);
        const scaleByWidth = availableWidth / (baseWidth + shellPadding);
        const scaleByHeight = availableHeight / (baseHeight + shellPadding);
        const scaleFactor = Math.max(0.1, Math.min(maxScaleCap, scaleByWidth, scaleByHeight));
        
        // Apply the scale factor
        const scaledContentWidth = Math.round(baseWidth * scaleFactor);
        const scaledContentHeight = Math.round(baseHeight * scaleFactor);
        
        console.log(`Original stream/base dimensions: ${baseWidth}x${baseHeight}, Scaled content: ${scaledContentWidth}x${scaledContentHeight} (scale: ${scaleFactor.toFixed(2)})`);
        
        // Calculate exact window size to match device display area + chrome
        const windowWidth = scaledContentWidth + shellPadding; // add horizontal shell padding
        const windowHeight = scaledContentHeight + shellPadding + headerHeight + footerHeight;
        
        console.log(`Creating window content size: ${scaledContentWidth}x${scaledContentHeight}, window size: ${windowWidth}x${windowHeight}`);
        
        // Set icon based on platform
        let icon;
        if (process.platform === 'win32') {
            icon = path.join(__dirname, '..', 'assets', 'icons', 'icon.ico');
        } else if (process.platform === 'darwin') {
            icon = path.join(__dirname, '..', 'assets', 'icons', 'icon.icns');
        } else {
            // Linux and other platforms
            icon = path.join(__dirname, '..', 'assets', 'icons', 'icon.png');
        }

        this.mainWindow = new BrowserWindow({
            width: windowWidth,
            height: windowHeight,
            // Removed fixed min sizes so programmatic resizes (e.g., on rotation) can shrink window
            resizable: false, // prevent user from resizing beyond device frame
            icon: icon,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            title: `iOS Bridge - ${this.config?.sessionInfo?.device_type || 'iOS Simulator'}`,
            titleBarStyle: 'default',
            show: false,
            alwaysOnTop: this.config?.alwaysOnTop || false,
            backgroundColor: '#1a1a1a'
        });
        
        // Create menu
        this.createMenu();
        
        // Load the main page
        this.mainWindow.loadFile(path.join(__dirname, 'renderer.html'));
        
        // Show window when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
            
            if (this.config?.fullscreen) {
                this.mainWindow.setFullScreen(true);
            }
        });
        
        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
            if (!this.isQuitting) {
                app.quit();
            }
        });
        
        // Development tools - only open in dev mode
        if (process.argv.includes('--dev')) {
            this.mainWindow.webContents.openDevTools();
        }
        
        // Forward console messages to main process (but filter out noisy ones)
        this.mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
            // Skip noisy security warnings and autofill messages
            if (message.includes('Content-Security-Policy') || 
                message.includes('Autofill.enable') || 
                message.includes('Autofill.setAddresses')) {
                return;
            }
            
            const levelMap = { 0: 'LOG', 1: 'WARN', 2: 'ERROR' };
            const levelName = levelMap[level] || 'LOG';
            console.log(`[RENDERER-${levelName}] ${message}`);
        });
        
        // Also capture console API calls directly
        this.mainWindow.webContents.executeJavaScript(`
            const originalLog = console.log;
            const originalWarn = console.warn;
            const originalError = console.error;
            
            console.log = function(...args) {
                originalLog.apply(console, args);
            };
            console.warn = function(...args) {
                originalWarn.apply(console, args);
            };
            console.error = function(...args) {
                originalError.apply(console, args);
            };
        `);
        
        // Add keyboard shortcuts
        this.mainWindow.webContents.on('before-input-event', (event, input) => {
            // Toggle dev tools: Ctrl+Shift+I (Windows/Linux) or Cmd+Option+I (Mac)
            if ((input.control && input.shift && input.key.toLowerCase() === 'i') ||
                (input.meta && input.alt && input.key.toLowerCase() === 'i')) {
                this.mainWindow.webContents.toggleDevTools();
            }
            
            // Force dev tools open: F12
            if (input.key === 'F12') {
                this.mainWindow.webContents.openDevTools();
            }
            
            // Copy in dev tools: Ctrl+C or Cmd+C
            if ((input.control || input.meta) && input.key.toLowerCase() === 'c') {
                // Let the dev tools handle copy
                return;
            }
        });
    }
    
    createMenu() {
        const template = [
            {
                label: 'iOS Bridge',
                submenu: [
                    {
                        label: 'About iOS Bridge',
                        role: 'about'
                    },
                    { type: 'separator' },
                    {
                        label: 'Quit',
                        accelerator: 'CmdOrCtrl+Q',
                        click: () => {
                            this.isQuitting = true;
                            app.quit();
                        }
                    }
                ]
            },
            {
                label: 'Device',
                submenu: [
                    {
                        label: 'Home Button',
                        accelerator: 'F1',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'home');
                        }
                    },
                    {
                        label: 'Screenshot',
                        accelerator: 'F2',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'screenshot');
                        }
                    },
                    {
                        label: 'Device Info',
                        accelerator: 'F3',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'info');
                        }
                    },
                    {
                        label: 'Toggle Keyboard',
                        accelerator: 'F4',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'keyboard');
                        }
                    },
                    {
                        label: 'Lock Device',
                        accelerator: 'F5',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'lock');
                        }
                    },
                    {
                        label: 'Start Recording',
                        accelerator: 'F6',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'record');
                        }
                    },
                    {
                        label: 'Stop Recording',
                        accelerator: 'F7',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'stop-record');
                        }
                    }
                ]
            },
            {
                label: 'View',
                submenu: [
                    {
                        label: 'Toggle Fullscreen',
                        accelerator: 'F11',
                        click: () => {
                            if (this.mainWindow) {
                                const isFullScreen = this.mainWindow.isFullScreen();
                                this.mainWindow.setFullScreen(!isFullScreen);
                            }
                        }
                    },
                    {
                        label: 'Always on Top',
                        type: 'checkbox',
                        checked: this.config?.alwaysOnTop || false,
                        click: (menuItem) => {
                            this.mainWindow?.setAlwaysOnTop(menuItem.checked);
                        }
                    },
                    { type: 'separator' },
                    {
                        label: 'Reload',
                        accelerator: 'CmdOrCtrl+R',
                        click: () => {
                            this.mainWindow?.reload();
                        }
                    },
                    {
                        label: 'Force Reload',
                        accelerator: 'CmdOrCtrl+Shift+R',
                        click: () => {
                            this.mainWindow?.webContents.reloadIgnoringCache();
                        }
                    }
                ]
            }
        ];
        
        // Add development menu in dev mode
        if (process.argv.includes('--dev')) {
            template.push({
                label: 'Development',
                submenu: [
                    {
                        label: 'Toggle Developer Tools',
                        accelerator: 'F12',
                        click: () => {
                            this.mainWindow?.webContents.toggleDevTools();
                        }
                    }
                ]
            });
        }
        
        const menu = Menu.buildFromTemplate(template);
        Menu.setApplicationMenu(menu);
    }
}

// Create and start the app
new IOSBridgeApp();