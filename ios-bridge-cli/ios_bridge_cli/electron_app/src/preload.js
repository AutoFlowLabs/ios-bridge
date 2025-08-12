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
    
    // Device actions
    onDeviceAction: (callback) => {
        ipcRenderer.on('device-action', (event, action) => callback(action));
    },
    
    // Remove listeners
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    }
});