import React, { useState, useEffect, useCallback } from 'react';
import Login from './Login';
import EditSwitches from './EditSwitches';
import './App.css';

// Auth context helper
const getAuthToken = () => localStorage.getItem('cherrypi-token');
const getAuthUser = () => {
  const user = localStorage.getItem('cherrypi-user');
  return user ? JSON.parse(user) : null;
};
const setAuthData = (token, user) => {
  localStorage.setItem('cherrypi-token', token);
  localStorage.setItem('cherrypi-user', JSON.stringify(user));
};
const clearAuthData = () => {
  localStorage.removeItem('cherrypi-token');
  localStorage.removeItem('cherrypi-user');
};

// Helper to make authenticated API calls
const authFetch = async (url, options = {}) => {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };
  
  const response = await fetch(url, { ...options, headers });
  
  // Handle 401 - token expired or invalid
  if (response.status === 401) {
    clearAuthData();
    window.location.reload();
    throw new Error('Session expired');
  }
  
  return response;
};

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(true);
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('control');
  const [switches, setSwitches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('cherrypi-theme') || 'dark';
  });

  // Check for existing auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // First check if auth is enabled on the server
        const statusResponse = await fetch('/api/auth/status');
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          if (!statusData.auth_enabled) {
            // Auth disabled - auto-login as anonymous admin
            setAuthEnabled(false);
            setIsLoggedIn(true);
            setUser({ username: 'anonymous', role: 'admin' });
            setLoading(false);
            return;
          }
        }
      } catch (e) {
        // If status check fails, assume auth is enabled
        console.log('Auth status check failed, assuming auth enabled');
      }

      // Auth is enabled - check for existing token
      const token = getAuthToken();
      const savedUser = getAuthUser();
      
      if (token && savedUser) {
        // Verify token is still valid
        try {
          const response = await authFetch('/api/auth/verify', { method: 'POST' });
          if (response.ok) {
            setIsLoggedIn(true);
            setUser(savedUser);
          } else {
            clearAuthData();
          }
        } catch {
          clearAuthData();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cherrypi-theme', theme);
  }, [theme]);

  // Fetch switches from API
  const fetchSwitches = useCallback(async () => {
    try {
      setLoading(true);
      // Use secure endpoint if logged in, otherwise try public endpoint
      const endpoint = isLoggedIn ? '/api/secure/switches' : '/api/switches';
      const response = await authFetch(endpoint);
      if (response.ok) {
        const data = await response.json();
        setSwitches(data);
      } else {
        console.error('Failed to fetch switches');
        setSwitches([]);
      }
    } catch (error) {
      console.error('Error fetching switches:', error);
      setSwitches([]);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (isLoggedIn && currentPage === 'control') {
      fetchSwitches();
    }
  }, [isLoggedIn, currentPage, fetchSwitches]);

  const handleLogin = (token, userData) => {
    setAuthData(token, userData);
    setIsLoggedIn(true);
    setUser(userData);
  };

  const handleLogout = () => {
    clearAuthData();
    setIsLoggedIn(false);
    setUser(null);
  };

  const handleToggle = async (outletId, state) => {
    console.log(`Outlet ${outletId} turned ${state}`);
    try {
      // Use secure endpoint for authenticated users
      const endpoint = isLoggedIn ? '/api/secure/outlet' : '/api/outlet';
      const response = await authFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ outlet_id: outletId, state: state }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Error:', errorData);
        alert(`Failed to turn ${state} Outlet ${outletId}: ${errorData.detail}`);
      } else {
        const data = await response.json();
        console.log('Success:', data);
      }
    } catch (error) {
      console.error('Network Error:', error);
      alert('Failed to connect to the server.');
    }
  };

  // Check if user can edit switches (admin or user role)
  const canEditSwitches = user && (user.role === 'admin' || user.role === 'user');

  if (!isLoggedIn) {
    return (
      <div className="App">
        <header className="App-header">
          <div className="login-header">
            <h1>🍒 CherryPi</h1>
          </div>
          <Login onLogin={handleLogin} theme={theme} onThemeToggle={setTheme} />
        </header>
      </div>
    );
  }

  // Show Edit Switches page
  if (currentPage === 'edit') {
    return (
      <div className="App">
        {/* Top Navigation Bar */}
        <nav className="top-bar">
          <div className="top-bar-content">
            <h1>🍒 CherryPi</h1>
            
            <div className="top-tabs">
              <button 
                className={`tab-btn ${currentPage === 'control' ? 'active' : ''}`}
                onClick={() => { setCurrentPage('control'); fetchSwitches(); }}
              >
                <span className="tab-icon">🎮</span>
                <span className="tab-label">Control</span>
              </button>
              {canEditSwitches && (
                <button 
                  className={`tab-btn ${currentPage === 'edit' ? 'active' : ''}`}
                  onClick={() => setCurrentPage('edit')}
                >
                  <span className="tab-icon">⚙️</span>
                  <span className="tab-label">Edit</span>
                </button>
              )}
              <a 
                href={`${window.location.protocol}//${window.location.hostname}:8080`}
                target="_blank"
                rel="noopener noreferrer"
                className="tab-btn tab-link"
              >
                <span className="tab-icon">🏠</span>
                <span className="tab-label">Foundation</span>
              </a>
            </div>
            
            <div className="top-bar-right">
              <div className="user-info-compact">
                <span className="username-compact">{user?.username}</span>
                <span className={`role-badge role-${user?.role}`}>{user?.role}</span>
              </div>
              {authEnabled && (
                <button className="btn btn-secondary btn-logout" onClick={handleLogout}>
                  <span className="tab-icon">🚪</span>
                  <span className="logout-text">Logout</span>
                </button>
              )}
            </div>
          </div>
        </nav>
        
        <main className="main-content">
          <EditSwitches 
            onBack={() => { setCurrentPage('control'); fetchSwitches(); }}
            authFetch={authFetch}
          />
        </main>
      </div>
    );
  }

  // Main Control page
  return (
    <div className="App">
      {/* Top Navigation Bar */}
      <nav className="top-bar">
        <div className="top-bar-content">
          <h1>🍒 CherryPi</h1>
          
          <div className="top-tabs">
            <button 
              className={`tab-btn ${currentPage === 'control' ? 'active' : ''}`}
              onClick={() => setCurrentPage('control')}
            >
              <span className="tab-icon">🎮</span>
              <span className="tab-label">Control</span>
            </button>
            {canEditSwitches && (
              <button 
                className={`tab-btn ${currentPage === 'edit' ? 'active' : ''}`}
                onClick={() => setCurrentPage('edit')}
              >
                <span className="tab-icon">⚙️</span>
                <span className="tab-label">Edit</span>
              </button>
            )}
            <a 
              href={`${window.location.protocol}//${window.location.hostname}:8080`}
              target="_blank"
              rel="noopener noreferrer"
              className="tab-btn tab-link"
            >
              <span className="tab-icon">🏠</span>
              <span className="tab-label">Foundation</span>
            </a>
          </div>
          
          <div className="top-bar-right">
            <div className="user-info-compact">
              <span className="username-compact">{user?.username}</span>
              <span className={`role-badge role-${user?.role}`}>{user?.role}</span>
            </div>
            {authEnabled && (
              <button className="btn btn-secondary btn-logout" onClick={handleLogout}>
                <span className="tab-icon">🚪</span>
                <span className="logout-text">Logout</span>
              </button>
            )}
          </div>
        </div>
      </nav>
      
      <main className="main-content">
        {loading ? (
          <p className="loading-message">Loading switches...</p>
        ) : switches.length === 0 ? (
          <div className="no-switches-message">
            <p>No switches configured yet.</p>
            {canEditSwitches && (
              <button 
                className="btn btn-primary" 
                onClick={() => setCurrentPage('edit')}
              >
                + Add Your First Switch
              </button>
            )}
          </div>
        ) : (
          <div className="switch-grid">
            {switches.map((sw) => (
              <div key={sw.id} className="switch-card">
                <span className="switch-name">{sw.name}</span>
                <div className="switch-buttons">
                  <button 
                    className="btn btn-on" 
                    onClick={() => handleToggle(sw.id, 'on')}
                  >
                    ON
                  </button>
                  <button 
                    className="btn btn-off" 
                    onClick={() => handleToggle(sw.id, 'off')}
                  >
                    OFF
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
