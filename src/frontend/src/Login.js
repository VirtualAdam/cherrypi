import React, { useState } from 'react';
import './App.css';

function Login({ onLogin, theme, onThemeToggle }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simple hardcoded check for demonstration
    // In a real app, this would call a backend API
    if (username === 'admin' && password === 'raspberry') {
      onLogin(true);
    } else {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="login-container">
      <div className="theme-toggle">
        <button 
          className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
          onClick={() => onThemeToggle('light')}
        >
          ☀️ Light
        </button>
        <button 
          className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
          onClick={() => onThemeToggle('dark')}
        >
          🌙 Dark
        </button>
      </div>
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>Login</h2>
        {error && <div className="error-message">{error}</div>}
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
          />
        </div>
        <button type="submit" className="btn btn-login">Sign In</button>
      </form>
    </div>
  );
}

export default Login;
