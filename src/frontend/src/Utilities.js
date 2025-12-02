import React, { useState, useEffect } from 'react';
import AddSwitchWizard from './AddSwitchWizard';
import './Utilities.css';

function Utilities({ onBack }) {
  const [switches, setSwitches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [editingSwitch, setEditingSwitch] = useState(null);

  // Fetch switches on mount
  useEffect(() => {
    fetchSwitches();
  }, []);

  const fetchSwitches = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/switches');
      if (!response.ok) {
        throw new Error('Failed to fetch switches');
      }
      const data = await response.json();
      setSwitches(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching switches:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (switchId) => {
    if (!window.confirm(`Are you sure you want to delete switch ${switchId}?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/switches/${switchId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete switch');
      }

      // Refresh the list
      fetchSwitches();
    } catch (err) {
      alert(`Error deleting switch: ${err.message}`);
    }
  };

  const handleEdit = (sw) => {
    setEditingSwitch(sw);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch(`/api/switches/${editingSwitch.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingSwitch.name,
          on_code: editingSwitch.on_code,
          off_code: editingSwitch.off_code,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update switch');
      }

      setEditingSwitch(null);
      fetchSwitches();
    } catch (err) {
      alert(`Error updating switch: ${err.message}`);
    }
  };

  const handleWizardComplete = (newSwitch) => {
    setShowWizard(false);
    fetchSwitches();
  };

  if (loading) {
    return (
      <div className="utilities-container">
        <div className="utilities-header">
          <button className="btn btn-back" onClick={onBack}>← Back</button>
          <h2>Utilities</h2>
        </div>
        <p className="loading">Loading switches...</p>
      </div>
    );
  }

  return (
    <div className="utilities-container">
      <div className="utilities-header">
        <button className="btn btn-back" onClick={onBack}>← Back</button>
        <h2>Switch Management</h2>
      </div>

      {error && <p className="error">Error: {error}</p>}

      <div className="switches-list">
        <div className="switches-header">
          <span>ID</span>
          <span>Name</span>
          <span>ON Code</span>
          <span>OFF Code</span>
          <span>Actions</span>
        </div>

        {switches.map((sw) => (
          <div key={sw.id} className="switch-row">
            {editingSwitch && editingSwitch.id === sw.id ? (
              // Edit mode
              <form onSubmit={handleSaveEdit} className="edit-form">
                <span className="switch-id">{sw.id}</span>
                <input
                  type="text"
                  value={editingSwitch.name}
                  onChange={(e) => setEditingSwitch({ ...editingSwitch, name: e.target.value })}
                  className="edit-input"
                />
                <input
                  type="number"
                  value={editingSwitch.on_code}
                  onChange={(e) => setEditingSwitch({ ...editingSwitch, on_code: parseInt(e.target.value) })}
                  className="edit-input"
                />
                <input
                  type="number"
                  value={editingSwitch.off_code}
                  onChange={(e) => setEditingSwitch({ ...editingSwitch, off_code: parseInt(e.target.value) })}
                  className="edit-input"
                />
                <div className="action-buttons">
                  <button type="submit" className="btn btn-save">Save</button>
                  <button type="button" className="btn btn-cancel" onClick={() => setEditingSwitch(null)}>Cancel</button>
                </div>
              </form>
            ) : (
              // View mode
              <>
                <span className="switch-id">{sw.id}</span>
                <span className="switch-name">{sw.name}</span>
                <span className="switch-code">{sw.on_code}</span>
                <span className="switch-code">{sw.off_code}</span>
                <div className="action-buttons">
                  <button className="btn btn-edit" onClick={() => handleEdit(sw)}>Edit</button>
                  <button className="btn btn-delete" onClick={() => handleDelete(sw.id)}>Delete</button>
                </div>
              </>
            )}
          </div>
        ))}

        {switches.length === 0 && (
          <p className="no-switches">No switches configured. Add your first switch!</p>
        )}
      </div>

      <div className="add-switch-section">
        <button 
          className="btn btn-add-switch" 
          onClick={() => setShowWizard(true)}
        >
          + Add New Switch
        </button>
      </div>

      {showWizard && (
        <AddSwitchWizard
          onComplete={handleWizardComplete}
          onCancel={() => setShowWizard(false)}
          existingSwitches={switches}
        />
      )}
    </div>
  );
}

export default Utilities;
