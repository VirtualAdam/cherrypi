import React, { useState, useEffect, useCallback } from 'react';
import './EditSwitches.css';

function EditSwitches({ onBack, authFetch }) {
  const [switches, setSwitches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newSwitch, setNewSwitch] = useState(null);
  const [scanningState, setScanningState] = useState({});

  // Use authFetch if provided, otherwise fall back to regular fetch
  const apiFetch = useCallback((url, options) => {
    return authFetch ? authFetch(url, options) : fetch(url, options);
  }, [authFetch]);

  const fetchSwitches = useCallback(async () => {
    try {
      setLoading(true);
      const endpoint = authFetch ? '/api/secure/switches' : '/api/switches';
      const response = await apiFetch(endpoint);
      if (!response.ok) throw new Error('Failed to fetch switches');
      const data = await response.json();
      setSwitches(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, authFetch]);

  useEffect(() => {
    fetchSwitches();
  }, [fetchSwitches]);

  const handleScan = async (codeType) => {
    const scanKey = `new-${codeType}`;
    setScanningState(prev => ({ ...prev, [scanKey]: 'listening' }));

    try {
      const response = await apiFetch('/api/sniffer/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capture_type: codeType }),
      });

      const result = await response.json();

      if (result.event === 'captured' && result.code) {
        setNewSwitch(prev => ({
          ...prev,
          [codeType === 'on' ? 'on_code' : 'off_code']: result.code
        }));
        setScanningState(prev => ({ ...prev, [scanKey]: null }));
      } else {
        const errorMsg = result.error || result.message || 'No code captured';
        setScanningState(prev => ({ ...prev, [scanKey]: null }));
        alert(`Scan failed: ${errorMsg}`);
      }
    } catch (err) {
      setScanningState(prev => ({ ...prev, [scanKey]: null }));
      alert(`Scan error: ${err.message}`);
    }
  };

  const handleDelete = async (switchId, switchName) => {
    if (!window.confirm(`Delete "${switchName}"?`)) return;
    
    try {
      const endpoint = authFetch ? `/api/secure/switches/${switchId}` : `/api/switches/${switchId}`;
      await apiFetch(endpoint, { method: 'DELETE' });
      fetchSwitches();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleAddSwitch = () => {
    setNewSwitch({ name: '', on_code: null, off_code: null });
  };

  const handleSaveNewSwitch = async () => {
    if (!newSwitch.name.trim()) {
      alert('Please enter a name for the switch.');
      return;
    }
    if (!newSwitch.on_code || !newSwitch.off_code) {
      alert('Please scan both ON and OFF codes before saving.');
      return;
    }

    try {
      const endpoint = authFetch ? '/api/secure/switches' : '/api/switches';
      const response = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSwitch),
      });

      if (!response.ok) throw new Error('Failed to create switch');
      
      setNewSwitch(null);
      fetchSwitches();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleCancelNewSwitch = () => {
    setNewSwitch(null);
  };

  if (loading) {
    return (
      <div className="edit-container">
        <div className="edit-header">
          <button className="btn btn-back" onClick={onBack}>← Back</button>
          <h2>Edit Switches</h2>
        </div>
        <p className="loading-text">Loading...</p>
      </div>
    );
  }

  return (
    <div className="edit-container">
      <div className="edit-header">
        <button className="btn btn-back" onClick={onBack}>← Back</button>
        <h2>Edit Switches</h2>
      </div>

      {error && <p className="error-text">Error: {error}</p>}

      <div className="edit-table">
        <div className="table-header-row">
          <span className="col-name">Name</span>
          <span className="col-code">ON Code</span>
          <span className="col-code">OFF Code</span>
          <span className="col-action"></span>
        </div>

        {switches.map((sw) => (
          <div key={sw.id} className="table-row">
            <span className="col-name">{sw.name}</span>
            <span className="col-code code-value">{sw.on_code}</span>
            <span className="col-code code-value">{sw.off_code}</span>
            <span className="col-action">
              <button 
                className="btn btn-delete"
                onClick={() => handleDelete(sw.id, sw.name)}
              >
                Delete
              </button>
            </span>
          </div>
        ))}

        {/* New Switch Row */}
        {newSwitch && (
          <div className="table-row new-row">
            <span className="col-name">
              <input
                type="text"
                className="input-name"
                value={newSwitch.name}
                onChange={(e) => setNewSwitch(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Switch name"
                autoFocus
              />
            </span>
            <span className="col-code">
              {scanningState['new-on'] === 'listening' ? (
                <span className="scanning">Listening...</span>
              ) : newSwitch.on_code ? (
                <span className="code-value">{newSwitch.on_code}</span>
              ) : (
                <button className="btn btn-scan" onClick={() => handleScan('on')}>
                  Scan ON
                </button>
              )}
            </span>
            <span className="col-code">
              {scanningState['new-off'] === 'listening' ? (
                <span className="scanning">Listening...</span>
              ) : newSwitch.off_code ? (
                <span className="code-value">{newSwitch.off_code}</span>
              ) : (
                <button className="btn btn-scan" onClick={() => handleScan('off')}>
                  Scan OFF
                </button>
              )}
            </span>
            <span className="col-action new-actions">
              <button className="btn btn-save" onClick={handleSaveNewSwitch}>Save</button>
              <button className="btn btn-cancel" onClick={handleCancelNewSwitch}>Cancel</button>
            </span>
          </div>
        )}

        {switches.length === 0 && !newSwitch && (
          <p className="empty-message">No switches configured yet.</p>
        )}
      </div>

      {!newSwitch && (
        <div className="add-section">
          <button className="btn btn-add" onClick={handleAddSwitch}>
            + Add Switch
          </button>
        </div>
      )}
    </div>
  );
}

export default EditSwitches;
