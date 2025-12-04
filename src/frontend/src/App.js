import React, { useState, useEffect } from 'react';
import Login from './Login';
import EditSwitches from './EditSwitches';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentPage, setCurrentPage] = useState('control');
  const [switches, setSwitches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('cherrypi-theme') || 'dark';
  });

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cherrypi-theme', theme);
  }, [theme]);

  // Fetch switches from API
  useEffect(() => {
    if (isLoggedIn && currentPage === 'control') {
      fetchSwitches();
    }
  }, [isLoggedIn, currentPage]);

  const fetchSwitches = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/switches');
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
  };

  const handleToggle = async (outletId, state) => {
    console.log(`Outlet ${outletId} turned ${state}`);
    try {
      const response = await fetch('/api/outlet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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

  if (!isLoggedIn) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>CherryPi</h1>
          <Login onLogin={setIsLoggedIn} theme={theme} onThemeToggle={setTheme} />
        </header>
      </div>
    );
  }

  // Show Edit Switches page
  if (currentPage === 'edit') {
    return (
      <div className="App">
        <header className="App-header">
          <EditSwitches onBack={() => { setCurrentPage('control'); fetchSwitches(); }} />
        </header>
      </div>
    );
  }

  // Main Control page
  return (
    <div className="App">
      <header className="App-header">
        <div className="header-top">
          <h1>CherryPi</h1>
          <div className="header-buttons">
            <button className="btn btn-secondary" onClick={() => setCurrentPage('edit')}>
              Edit
            </button>
            <button className="btn btn-secondary" onClick={() => setIsLoggedIn(false)}>
              Logout
            </button>
          </div>
        </div>
        
        {loading ? (
          <p className="loading-message">Loading switches...</p>
        ) : switches.length === 0 ? (
          <div className="no-switches-message">
            <p>No switches configured yet.</p>
            <button 
              className="btn btn-primary" 
              onClick={() => setCurrentPage('edit')}
            >
              + Add Your First Switch
            </button>
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
      </header>
    </div>
  );
}

export default App;
