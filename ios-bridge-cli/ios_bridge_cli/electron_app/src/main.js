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
        
        app.on('before-quit', () => {
            this.isQuitting = true;
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
    }
    
    createWindow() {
        const primaryDisplay = screen.getPrimaryDisplay();
        const { width, height } = primaryDisplay.workAreaSize;
        
        // Calculate window size based on device dimensions
        const deviceWidth = 390;  // iPhone default width
        const deviceHeight = 844; // iPhone default height
        const scale = Math.min(width * 0.6 / deviceWidth, height * 0.8 / deviceHeight);
        
        const windowWidth = Math.floor(deviceWidth * scale) + 100; // Extra space for controls
        const windowHeight = Math.floor(deviceHeight * scale) + 150; // Extra space for title bar and controls
        
        this.mainWindow = new BrowserWindow({
            width: windowWidth,
            height: windowHeight,
            minWidth: 400,
            minHeight: 600,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            },
            title: `iOS Bridge - ${this.config?.sessionInfo?.device_type || 'iOS Simulator'}`,
            titleBarStyle: 'default',
            show: false,
            alwaysOnTop: this.config?.alwaysOnTop || false
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
        
        // Development tools
        if (process.argv.includes('--dev')) {
            this.mainWindow.webContents.openDevTools();
        }
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
                    { type: 'separator' },
                    {
                        label: 'Lock Device',
                        accelerator: 'CmdOrCtrl+L',
                        click: () => {
                            this.mainWindow?.webContents.send('device-action', 'lock');
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