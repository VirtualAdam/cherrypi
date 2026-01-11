import React, { useState, useEffect } from 'react';
import './App.css';

function Login({ onLogin, theme, onThemeToggle }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [magicCode, setMagicCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginMode, setLoginMode] = useState('password'); // 'password' or 'magic'

  // Check for magic code in URL (from QR scan)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      setMagicCode(code.toUpperCase());
      setLoginMode('magic');
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        onLogin(data.token, {
          username: data.username,
          role: data.role
        });
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleMagicLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/magic/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          code: magicCode.toUpperCase().trim(),
          role: 'user' // Request user role for magic login
        }),
      });

      const data = await response.json();

      if (response.ok) {
        onLogin(data.token, {
          username: `device_${magicCode.substring(0, 4)}`,
          role: data.role
        });
      } else {
        setError(data.detail || 'Invalid or expired magic code');
      }
    } catch (err) {
      console.error('Magic login error:', err);
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const formatMagicCode = (value) => {
    // Only allow alphanumeric, convert to uppercase
    return value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().substring(0, 8);
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

      <div className="login-mode-toggle">
        <button
          className={`mode-btn ${loginMode === 'password' ? 'active' : ''}`}
          onClick={() => { setLoginMode('password'); setError(''); }}
        >
          🔑 Password
        </button>
        <button
          className={`mode-btn ${loginMode === 'magic' ? 'active' : ''}`}
          onClick={() => { setLoginMode('magic'); setError(''); }}
        >
          ✨ Magic Code
        </button>
      </div>

      <a 
        href="/foundation"
        className="foundation-link"
      >
        <span className="foundation-icon">🏠</span>
        <span>Wiedemann Family Foundation</span>
      </a>

      {loginMode === 'password' ? (
        <form className="login-form" onSubmit={handlePasswordLogin}>
          <h2>Login</h2>
          {error && <div className="error-message">{error}</div>}
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading}
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="btn btn-login" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      ) : (
        <form className="login-form" onSubmit={handleMagicLogin}>
          <h2>Magic Code Login</h2>
          <p className="magic-code-hint">
            Enter the code from the QR display or scan the QR code with your device.
          </p>
          {error && <div className="error-message">{error}</div>}
          <div className="form-group">
            <label>Magic Code</label>
            <input
              type="text"
              value={magicCode}
              onChange={(e) => setMagicCode(formatMagicCode(e.target.value))}
              placeholder="ABCD1234"
              disabled={loading}
              className="magic-code-input"
              maxLength={8}
              autoComplete="off"
            />
          </div>
          <button 
            type="submit" 
            className="btn btn-login btn-magic" 
            disabled={loading || magicCode.length < 8}
          >
            {loading ? 'Verifying...' : '✨ Login with Magic Code'}
          </button>
        </form>
      )}
    </div>
  );
}

export default Login;
