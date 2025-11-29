import React, { useState } from 'react';
import Login from './Login';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const outlets = [1, 2, 3, 4, 5];

  const handleToggle = (outletId, state) => {
    console.log(`Outlet ${outletId} turned ${state}`);
    // TODO: Call backend API
    // fetch('/api/toggle', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ outletId, state })
    // });
  };

  if (!isLoggedIn) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>CherryPi Control</h1>
          <Login onLogin={setIsLoggedIn} />
        </header>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-top">
          <h1>CherryPi Control</h1>
          <button className="btn btn-logout" onClick={() => setIsLoggedIn(false)}>Logout</button>
        </div>
        <div className="outlet-grid">
          {outlets.map((id) => (
            <div key={id} className="outlet-row">
              <span className="outlet-label">Outlet {id}</span>
              <button 
                className="btn btn-on" 
                onClick={() => handleToggle(id, 'on')}
              >
                ON
              </button>
              <button 
                className="btn btn-off" 
                onClick={() => handleToggle(id, 'off')}
              >
                OFF
              </button>
            </div>
          ))}
        </div>
      </header>
    </div>
  );
}

export default App;
