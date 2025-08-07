// Replace the entire location.js file with this simplified version:

// Location control variables
let locationCollapsed = false;
let predefinedCollapsed = false;
let currentLocation = null;
let predefinedLocations = [];

if (typeof SESSION_ID === 'undefined') {
    console.error('SESSION_ID not defined in location.js - trying to get it from window');
    if (typeof window !== 'undefined' && window.SESSION_ID) {
        const SESSION_ID = window.SESSION_ID;
        console.log('Got SESSION_ID from window:', SESSION_ID);
    } else {
        console.error('SESSION_ID not available anywhere!');
    }
} else {
    console.log('SESSION_ID available in location.js:', SESSION_ID);
}

// Initialize location functionality
async function initLocationControls() {
    await loadPredefinedLocations();

    // Add coordinate change listeners for reverse geocoding
    const latInput = document.getElementById('latitudeInput');
    const lngInput = document.getElementById('longitudeInput');

    if (latInput && lngInput) {
        latInput.addEventListener('input', debounce(reverseGeocode, 1000));
        lngInput.addEventListener('input', debounce(reverseGeocode, 1000));
    }
}

function toggleLocationSection() {
    const locationSection = document.getElementById('locationSection');
    const toggleIcon = document.getElementById('locationToggleIcon');

    locationCollapsed = !locationCollapsed;

    if (locationCollapsed) {
        locationSection.classList.add('collapsed');
        toggleIcon.classList.add('collapsed');
        toggleIcon.textContent = '▶';
        showTemporaryStatus('📍 Location controls collapsed');
    } else {
        locationSection.classList.remove('collapsed');
        toggleIcon.classList.remove('collapsed');
        toggleIcon.textContent = '▼';
        showTemporaryStatus('📍 Location controls expanded');
    }
}
function togglePredefinedLocations() {
    console.log('togglePredefinedLocations called');

    const predefinedList = document.getElementById('predefinedLocationsList');
    const toggleIcon = document.getElementById('predefinedToggleIcon');

    console.log('predefinedList:', predefinedList);
    console.log('toggleIcon:', toggleIcon);

    if (!predefinedList || !toggleIcon) {
        console.error('Required elements not found');
        return;
    }

    predefinedCollapsed = !predefinedCollapsed;
    console.log('predefinedCollapsed:', predefinedCollapsed);

    if (predefinedCollapsed) {
        predefinedList.classList.add('collapsed');
        toggleIcon.classList.add('collapsed');
        toggleIcon.textContent = '▶';
        console.log('Collapsed predefined locations');

        if (typeof showTemporaryStatus === 'function') {
            showTemporaryStatus('🌍 Predefined locations collapsed');
        }
    } else {
        predefinedList.classList.remove('collapsed');
        toggleIcon.classList.remove('collapsed');
        toggleIcon.textContent = '▼';
        console.log('Expanded predefined locations');

        if (typeof showTemporaryStatus === 'function') {
            showTemporaryStatus('🌍 Predefined locations expanded');
        }

        // Force load predefined locations if they haven't been loaded yet
        if (predefinedLocations.length === 0) {
            console.log('Predefined locations not loaded yet, loading now...');
            loadPredefinedLocations();
        } else {
            console.log('Predefined locations already loaded:', predefinedLocations.length);
        }
    }
}
async function loadPredefinedLocations() {
    console.log('loadPredefinedLocations called');

    try {
        // Use the existing presets from your backend
        const url = `/api/sessions/${SESSION_ID}/location/presets`;
        console.log('Fetching from URL:', url);

        const response = await fetch(url);
        console.log('Response status:', response.status);

        const data = await response.json();
        console.log('Response data:', data);

        if (data.success && data.presets) {
            predefinedLocations = data.presets;
            console.log('Loaded predefined locations:', predefinedLocations.length);
            displayPredefinedLocations();
        } else {
            console.error('Failed to load predefined locations:', data);
            document.getElementById('predefinedLocationsList').innerHTML =
                '<div class="predefined-loading">Failed to load locations</div>';
        }
    } catch (error) {
        console.error('Error loading predefined locations:', error);
        document.getElementById('predefinedLocationsList').innerHTML =
            '<div class="predefined-loading">Failed to load locations</div>';
    }
}

function displayPredefinedLocations() {
    const predefinedList = document.getElementById('predefinedLocationsList');

    if (!predefinedList) {
        console.error('predefinedLocationsList element not found');
        return;
    }

    if (predefinedLocations.length === 0) {
        predefinedList.innerHTML = '<div class="predefined-loading">No locations available</div>';
        return;
    }

    predefinedList.innerHTML = '';

    predefinedLocations.forEach((location, index) => {
        const item = document.createElement('div');
        item.className = 'predefined-item';

        // Enhanced click handler with visual feedback
        item.onclick = () => {
            console.log(`Clicked on location: ${location.name}`);
            fillPredefinedLocation(location);

            // Visual feedback
            item.style.background = '#28a745';
            item.style.color = 'white';
            setTimeout(() => {
                item.style.background = '';
                item.style.color = '';
            }, 300);
        };

        item.innerHTML = `
            <div class="predefined-name">${location.name}</div>
            <div class="predefined-coords">${location.latitude}, ${location.longitude}</div>
        `;

        predefinedList.appendChild(item);
        console.log(`Added predefined location ${index + 1}: ${location.name}`);
    });

    console.log(`Successfully displayed ${predefinedLocations.length} predefined locations`);
}
function fillPredefinedLocation(location) {
    console.log('fillPredefinedLocation called with:', location);

    const latInput = document.getElementById('latitudeInput');
    const lngInput = document.getElementById('longitudeInput');

    console.log('latitude input element:', latInput);
    console.log('longitude input element:', lngInput);

    if (latInput && lngInput) {
        // Fill the coordinates
        latInput.value = location.latitude;
        lngInput.value = location.longitude;

        console.log(`Filled coordinates: ${location.latitude}, ${location.longitude}`);

        // Show location name
        displayLocationName(location.name);

        // Trigger any input events that might be needed
        latInput.dispatchEvent(new Event('input', { bubbles: true }));
        lngInput.dispatchEvent(new Event('input', { bubbles: true }));

        // Show success message
        if (typeof showTemporaryStatus === 'function') {
            showTemporaryStatus(`📍 Filled coordinates for ${location.name}: ${location.latitude}, ${location.longitude}`);
        } else {
            console.log(`Status: Filled coordinates for ${location.name}`);
        }

        // Focus on latitude input for immediate editing if needed
        latInput.focus();

    } else {
        console.error('Latitude or longitude input elements not found');
        console.log('Available elements:', {
            latInput: !!latInput,
            lngInput: !!lngInput
        });
    }
}

async function setCustomLocation() {
    const latInput = document.getElementById('latitudeInput');
    const lngInput = document.getElementById('longitudeInput');

    const latitude = parseFloat(latInput.value);
    const longitude = parseFloat(lngInput.value);

    if (isNaN(latitude) || isNaN(longitude)) {
        showTemporaryStatus('❌ Please enter valid coordinates');
        return;
    }

    if (latitude < -90 || latitude > 90) {
        showTemporaryStatus('❌ Latitude must be between -90 and 90');
        return;
    }

    if (longitude < -180 || longitude > 180) {
        showTemporaryStatus('❌ Longitude must be between -180 and 180');
        return;
    }

    await setLocation(latitude, longitude, getDisplayedLocationName() || 'Custom Location');
}

async function setLocation(latitude, longitude, locationName = '') {
    try {
        showTemporaryStatus('📍 Setting location...');

        const formData = new FormData();
        formData.append('latitude', latitude.toString());
        formData.append('longitude', longitude.toString());

        const response = await fetch(`/api/sessions/${SESSION_ID}/location/set`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            currentLocation = {
                latitude: latitude,
                longitude: longitude,
                name: locationName || `${latitude}, ${longitude}`
            };

            updateLocationDisplay();
            showTemporaryStatus(`✅ Location set to ${currentLocation.name}`);

            // Keep the coordinates in the form for easy modification
            // Don't clear the input fields
        } else {
            showTemporaryStatus(`❌ Failed to set location: ${data.message}`);
        }

    } catch (error) {
        console.error('Error setting location:', error);
        showTemporaryStatus('❌ Error setting location');
    }
}

async function clearLocation() {
    try {
        showTemporaryStatus('📍 Clearing location...');

        const response = await fetch(`/api/sessions/${SESSION_ID}/location/clear`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            currentLocation = null;
            updateLocationDisplay();

            // Clear input fields when clearing location
            document.getElementById('latitudeInput').value = '';
            document.getElementById('longitudeInput').value = '';
            hideLocationName();

            showTemporaryStatus('✅ Mock location cleared');
        } else {
            showTemporaryStatus(`❌ Failed to clear location: ${data.message}`);
        }

    } catch (error) {
        console.error('Error clearing location:', error);
        showTemporaryStatus('❌ Error clearing location');
    }
}

function updateLocationDisplay() {
    const locationText = document.getElementById('currentLocationText');
    const clearBtn = document.getElementById('clearLocationBtn');

    if (currentLocation) {
        locationText.textContent = `📍 ${currentLocation.name}`;
        locationText.title = `${currentLocation.latitude}, ${currentLocation.longitude}`;
        clearBtn.style.display = 'inline-block';
    } else {
        locationText.textContent = 'No location set';
        locationText.title = '';
        clearBtn.style.display = 'none';
    }
}

function getCurrentCoordinates() {
    if (navigator.geolocation) {
        showTemporaryStatus('📍 Getting your current location...');

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                document.getElementById('latitudeInput').value = lat.toFixed(6);
                document.getElementById('longitudeInput').value = lng.toFixed(6);

                // Try to get location name
                await reverseGeocode();

                showTemporaryStatus(`✅ Current coordinates filled: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
            },
            (error) => {
                let message = 'Failed to get current location';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        message = 'Location access denied by user';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = 'Location information unavailable';
                        break;
                    case error.TIMEOUT:
                        message = 'Location request timed out';
                        break;
                }
                showTemporaryStatus(`❌ ${message}`);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 600000 // 10 minutes
            }
        );
    } else {
        showTemporaryStatus('❌ Geolocation not supported by browser');
    }
}

// Reverse geocoding to get location name from coordinates
async function reverseGeocode() {
    const latInput = document.getElementById('latitudeInput');
    const lngInput = document.getElementById('longitudeInput');

    const lat = parseFloat(latInput.value);
    const lng = parseFloat(lngInput.value);

    if (isNaN(lat) || isNaN(lng)) {
        hideLocationName();
        return;
    }

    try {
        // Using OpenStreetMap Nominatim for reverse geocoding (free, no API key needed)
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10&addressdetails=1`,
            {
                headers: {
                    'User-Agent': 'iOS-Bridge-Location-Tool'
                }
            }
        );

        if (response.ok) {
            const data = await response.json();
            if (data.display_name) {
                // Extract city and country for cleaner display
                const address = data.address || {};
                let locationName = '';

                if (address.city || address.town || address.village) {
                    locationName = address.city || address.town || address.village;
                    if (address.country) {
                        locationName += `, ${address.country}`;
                    }
                } else if (address.state && address.country) {
                    locationName = `${address.state}, ${address.country}`;
                } else if (address.country) {
                    locationName = address.country;
                } else {
                    locationName = data.display_name.split(',').slice(0, 2).join(', ');
                }

                displayLocationName(locationName);
            } else {
                hideLocationName();
            }
        } else {
            hideLocationName();
        }
    } catch (error) {
        console.log('Reverse geocoding failed:', error);
        hideLocationName();
    }
}

function displayLocationName(name) {
    const nameDisplay = document.getElementById('locationNameDisplay');
    const nameText = document.getElementById('locationNameText');

    if (nameDisplay && nameText && name) {
        nameText.textContent = `📍 ${name}`;
        nameDisplay.style.display = 'block';
    }
}

function hideLocationName() {
    const nameDisplay = document.getElementById('locationNameDisplay');
    if (nameDisplay) {
        nameDisplay.style.display = 'none';
    }
}

function getDisplayedLocationName() {
    const nameText = document.getElementById('locationNameText');
    if (nameText && nameText.textContent) {
        return nameText.textContent.replace('📍 ', '');
    }
    return null;
}

// Utility function to debounce reverse geocoding
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Helper function for temporary status (should be available globally)
function showTemporaryStatus(message) {
    // This should be implemented by the parent application
    if (window.showTemporaryStatus) {
        window.showTemporaryStatus(message);
    } else {
        console.log('Status:', message);
    }
}

// Add these lines at the very end of your location.js file:

// Make functions globally available for HTML onclick handlers
window.toggleLocationSection = toggleLocationSection;
window.togglePredefinedLocations = togglePredefinedLocations;
window.setCustomLocation = setCustomLocation;
window.clearLocation = clearLocation;
window.getCurrentCoordinates = getCurrentCoordinates;
window.fillPredefinedLocation = fillPredefinedLocation;
window.loadPredefinedLocations = loadPredefinedLocations;
window.initLocationControls = initLocationControls;

// Also make them available as regular functions for compatibility
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        toggleLocationSection,
        togglePredefinedLocations,
        setCustomLocation,
        clearLocation,
        getCurrentCoordinates,
        initLocationControls

    };
}


