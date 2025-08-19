const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // Config
    getConfig: () => ipcRenderer.invoke('get-config'),
    
    // Window controls
    quitApp: () => ipcRenderer.invoke('quit-app'),
    minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
    toggleFullscreen: () => ipcRenderer.invoke('toggle-fullscreen'),
    setAlwaysOnTop: (alwaysOnTop) => ipcRenderer.invoke('set-always-on-top', alwaysOnTop),
    resizeWindow: (width, height) => {
        // Ensure width and height are valid numbers before passing to main process
        if (typeof width === 'number' && typeof height === 'number' && 
            !isNaN(width) && !isNaN(height) && width > 0 && height > 0) {
            return ipcRenderer.invoke('resize-window', width, height);
        } else {
            console.error(`Invalid dimensions in resizeWindow: width=${width}, height=${height}`);
            return Promise.resolve({ error: 'invalid_dimensions' });
        }
    },
    
    // Device actions
    onDeviceAction: (callback) => {
        ipcRenderer.on('device-action', (event, action) => callback(action));
    },
    
    // Remove listeners
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    },
    
    // File dialogs
    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),
    readFile: (filePath) => ipcRenderer.invoke('read-file', filePath)
});