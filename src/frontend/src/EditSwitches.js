import React, { useState, useEffect } from 'react';
import './EditSwitches.css';

function EditSwitches({ onBack }) {
  const [switches, setSwitches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newSwitch, setNewSwitch] = useState(null); // For adding new switch
  const [scanningState, setScanningState] = useState({}); // Track which cell is scanning
  const [editingName, setEditingName] = useState({}); // Track name edits

  useEffect(() => {
    fetchSwitches();
  }, []);

  const fetchSwitches = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/switches');
      if (!response.ok) throw new Error('Failed to fetch switches');
      const data = await response.json();
      setSwitches(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async (switchId, codeType) => {
    const scanKey = `${switchId}-${codeType}`;
    setScanningState(prev => ({ ...prev, [scanKey]: 'listening' }));

    try {
      const response = await fetch('/api/sniffer/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capture_type: codeType }),
      });

      const result = await response.json();

      if (result.event === 'captured' && result.code) {
        // Update the code
        if (switchId === 'new') {
          setNewSwitch(prev => ({
            ...prev,
            [codeType === 'on' ? 'on_code' : 'off_code']: result.code
          }));
        } else {
          // Update existing switch
          const sw = switches.find(s => s.id === switchId);
          const updateData = {
            name: sw.name,
            on_code: codeType === 'on' ? result.code : sw.on_code,
            off_code: codeType === 'off' ? result.code : sw.off_code,
          };
          
          await fetch(`/api/switches/${switchId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData),
          });
          
          fetchSwitches();
        }
        setScanningState(prev => ({ ...prev, [scanKey]: 'success' }));
        setTimeout(() => setScanningState(prev => ({ ...prev, [scanKey]: null })), 2000);
      } else {
        // Error or no code
        const errorMsg = result.error || result.message || 'No code captured';
        setScanningState(prev => ({ ...prev, [scanKey]: 'error' }));
        setTimeout(() => {
          setScanningState(prev => ({ ...prev, [scanKey]: null }));
          alert(`Scan failed: ${errorMsg}`);
        }, 500);
      }
    } catch (err) {
      setScanningState(prev => ({ ...prev, [scanKey]: 'error' }));
      setTimeout(() => {
        setScanningState(prev => ({ ...prev, [scanKey]: null }));
        alert(`Scan error: ${err.message}`);
      }, 500);
    }
  };

  const handleDelete = async (switchId) => {
    if (!window.confirm('Delete this switch?')) return;
    
    try {
      await fetch(`/api/switches/${switchId}`, { method: 'DELETE' });
      fetchSwitches();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleAddSwitch = () => {
    setNewSwitch({ name: 'New Switch', on_code: null, off_code: null });
  };

  const handleSaveNewSwitch = async () => {
    if (!newSwitch.on_code || !newSwitch.off_code) {
      alert('Please scan both ON and OFF codes before saving.');
      return;
    }

    try {
      const response = await fetch('/api/switches', {
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

  const handleNameChange = async (switchId, newName) => {
    if (switchId === 'new') {
      setNewSwitch(prev => ({ ...prev, name: newName }));
      return;
    }

    const sw = switches.find(s => s.id === switchId);
    try {
      await fetch(`/api/switches/${switchId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName,
          on_code: sw.on_code,
          off_code: sw.off_code,
        }),
      });
      fetchSwitches();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const startEditingName = (switchId, currentName) => {
    setEditingName(prev => ({ ...prev, [switchId]: currentName }));
  };

  const finishEditingName = (switchId) => {
    if (editingName[switchId] !== undefined) {
      handleNameChange(switchId, editingName[switchId]);
      setEditingName(prev => {
        const next = { ...prev };
        delete next[switchId];
        return next;
      });
    }
  };

  const renderCodeCell = (switchId, codeType, code) => {
    const scanKey = `${switchId}-${codeType}`;
    const state = scanningState[scanKey];

    if (state === 'listening') {
      return <span className="code-listening">📡 Listening...</span>;
    }
    if (state === 'success') {
      return <span className="code-success">✅ {code}</span>;
    }
    if (state === 'error') {
      return <span className="code-error">❌ Failed</span>;
    }

    return (
      <div className="code-cell">
        {code ? (
          <span className="code-value">{code}</span>
        ) : (
          <span className="code-empty">—</span>
        )}
        <button 
          className="btn-scan" 
          onClick={() => handleScan(switchId, codeType)}
          title={`Scan ${codeType.toUpperCase()} code`}
        >
          📡
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="edit-switches-container">
        <div className="edit-header">
          <button className="btn btn-back" onClick={onBack}>← Back</button>
          <h2>Edit Switches</h2>
        </div>
        <p className="loading">Loading...</p>
      </div>
    );
  }

  return (
    <div className="edit-switches-container">
      <div className="edit-header">
        <button className="btn btn-back" onClick={onBack}>← Back</button>
        <h2>Edit Switches</h2>
      </div>

      {error && <p className="error">Error: {error}</p>}

      <div className="switches-table">
        <div className="table-header">
          <span>Name</span>
          <span>ON Code</span>
          <span>OFF Code</span>
          <span></span>
        </div>

        {switches.map((sw) => (
          <div key={sw.id} className="table-row">
            <div className="name-cell">
              {editingName[sw.id] !== undefined ? (
                <input
                  type="text"
                  className="name-input"
                  value={editingName[sw.id]}
                  onChange={(e) => setEditingName(prev => ({ ...prev, [sw.id]: e.target.value }))}
                  onBlur={() => finishEditingName(sw.id)}
                  onKeyDown={(e) => e.key === 'Enter' && finishEditingName(sw.id)}
                  autoFocus
                />
              ) : (
                <span 
                  className="name-value" 
                  onClick={() => startEditingName(sw.id, sw.name)}
                  title="Click to edit"
                >
                  {sw.name}
                </span>
              )}
            </div>
            {renderCodeCell(sw.id, 'on', sw.on_code)}
            {renderCodeCell(sw.id, 'off', sw.off_code)}
            <div className="delete-cell">
              <button 
                className="btn-delete-icon" 
                onClick={() => handleDelete(sw.id)}
                title="Delete switch"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}

        {/* New Switch Row */}
        {newSwitch && (
          <div className="table-row new-row">
            <div className="name-cell">
              <input
                type="text"
                className="name-input"
                value={newSwitch.name}
                onChange={(e) => setNewSwitch(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Switch name"
                autoFocus
              />
            </div>
            {renderCodeCell('new', 'on', newSwitch.on_code)}
            {renderCodeCell('new', 'off', newSwitch.off_code)}
            <div className="new-row-actions">
              <button className="btn-save-new" onClick={handleSaveNewSwitch}>Save</button>
              <button className="btn-cancel-new" onClick={handleCancelNewSwitch}>✕</button>
            </div>
          </div>
        )}

        {switches.length === 0 && !newSwitch && (
          <p className="no-switches">No switches yet. Click "Add Switch" to get started!</p>
        )}
      </div>

      {!newSwitch && (
        <div className="add-section">
          <button className="btn-add" onClick={handleAddSwitch}>
            + Add Switch
          </button>
        </div>
      )}
    </div>
  );
}

export default EditSwitches;
