import React, { useState } from 'react';
import './AddSwitchWizard.css';

const WIZARD_STEPS = {
  INTRO: 'intro',
  CAPTURE_ON: 'capture_on',
  CAPTURE_OFF: 'capture_off',
  NAME_SWITCH: 'name_switch',
  COMPLETE: 'complete',
};

function AddSwitchWizard({ onComplete, onCancel, existingSwitches }) {
  const [step, setStep] = useState(WIZARD_STEPS.INTRO);
  const [onCode, setOnCode] = useState(null);
  const [offCode, setOffCode] = useState(null);
  const [switchName, setSwitchName] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState(null);
  const [captureMessage, setCaptureMessage] = useState('');

  // Calculate next ID
  const nextId = existingSwitches.length > 0 
    ? Math.max(...existingSwitches.map(s => s.id)) + 1 
    : 1;

  const startCapture = async (captureType) => {
    setIsCapturing(true);
    setError(null);
    setCaptureMessage(`Listening for ${captureType.toUpperCase()} button press...`);

    try {
      const response = await fetch('/api/sniffer/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ capture_type: captureType }),
      });

      if (!response.ok) {
        throw new Error('Failed to start sniffer');
      }

      const result = await response.json();

      if (result.event === 'captured') {
        if (captureType === 'on') {
          setOnCode(result.code);
          setCaptureMessage(`Captured ON code: ${result.code}`);
          setTimeout(() => setStep(WIZARD_STEPS.CAPTURE_OFF), 1500);
        } else {
          setOffCode(result.code);
          setCaptureMessage(`Captured OFF code: ${result.code}`);
          // Auto-generate switch name
          setSwitchName(`Switch ${nextId}`);
          setTimeout(() => setStep(WIZARD_STEPS.NAME_SWITCH), 1500);
        }
      } else if (result.event === 'timeout') {
        setError('No code received. Please try again and press the button on your remote.');
      } else if (result.event === 'error') {
        setError(result.error || 'Unknown error occurred');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsCapturing(false);
    }
  };

  const stopCapture = async () => {
    try {
      await fetch('/api/sniffer/stop', { method: 'POST' });
    } catch (err) {
      console.error('Error stopping sniffer:', err);
    }
    setIsCapturing(false);
  };

  const saveSwitch = async () => {
    if (!switchName.trim()) {
      setError('Please enter a name for the switch');
      return;
    }

    setError(null);

    try {
      const response = await fetch('/api/switches', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: switchName.trim(),
          on_code: onCode,
          off_code: offCode,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save switch');
      }

      const newSwitch = await response.json();
      setStep(WIZARD_STEPS.COMPLETE);
      
      // Auto-close after showing success
      setTimeout(() => {
        onComplete(newSwitch);
      }, 2000);
    } catch (err) {
      setError(`Error saving switch: ${err.message}`);
    }
  };

  const renderContent = () => {
    switch (step) {
      case WIZARD_STEPS.INTRO:
        return (
          <div className="wizard-step">
            <h3>Add New Switch</h3>
            <p>This wizard will help you capture the RF codes from your remote control.</p>
            <p>You'll need your RF remote control ready.</p>
            <div className="wizard-buttons">
              <button className="btn btn-primary" onClick={() => setStep(WIZARD_STEPS.CAPTURE_ON)}>
                Start →
              </button>
              <button className="btn btn-secondary" onClick={onCancel}>
                Cancel
              </button>
            </div>
          </div>
        );

      case WIZARD_STEPS.CAPTURE_ON:
        return (
          <div className="wizard-step">
            <h3>Step 1: Capture ON Code</h3>
            {!isCapturing ? (
              <>
                <p>Click the button below, then press the <strong>ON</strong> button on your remote control.</p>
                <div className="wizard-buttons">
                  <button 
                    className="btn btn-capture" 
                    onClick={() => startCapture('on')}
                  >
                    📡 Start Listening
                  </button>
                </div>
              </>
            ) : (
              <div className="capturing">
                <div className="spinner"></div>
                <p>{captureMessage}</p>
                <button className="btn btn-secondary" onClick={stopCapture}>
                  Cancel
                </button>
              </div>
            )}
            {onCode && (
              <div className="captured-code">
                ✅ ON Code: <code>{onCode}</code>
              </div>
            )}
            {error && <p className="error">{error}</p>}
          </div>
        );

      case WIZARD_STEPS.CAPTURE_OFF:
        return (
          <div className="wizard-step">
            <h3>Step 2: Capture OFF Code</h3>
            <div className="captured-code success">
              ✅ ON Code: <code>{onCode}</code>
            </div>
            {!isCapturing ? (
              <>
                <p>Now press the <strong>OFF</strong> button on your remote control.</p>
                <div className="wizard-buttons">
                  <button 
                    className="btn btn-capture" 
                    onClick={() => startCapture('off')}
                  >
                    📡 Start Listening
                  </button>
                </div>
              </>
            ) : (
              <div className="capturing">
                <div className="spinner"></div>
                <p>{captureMessage}</p>
                <button className="btn btn-secondary" onClick={stopCapture}>
                  Cancel
                </button>
              </div>
            )}
            {offCode && (
              <div className="captured-code">
                ✅ OFF Code: <code>{offCode}</code>
              </div>
            )}
            {error && <p className="error">{error}</p>}
          </div>
        );

      case WIZARD_STEPS.NAME_SWITCH:
        return (
          <div className="wizard-step">
            <h3>Step 3: Name Your Switch</h3>
            <div className="codes-summary">
              <div className="captured-code success">✅ ON Code: <code>{onCode}</code></div>
              <div className="captured-code success">✅ OFF Code: <code>{offCode}</code></div>
            </div>
            <div className="name-input-container">
              <label htmlFor="switch-name">Switch Name:</label>
              <input
                id="switch-name"
                type="text"
                value={switchName}
                onChange={(e) => setSwitchName(e.target.value)}
                placeholder={`Switch ${nextId}`}
                className="name-input"
                autoFocus
              />
              <p className="hint">ID will be assigned automatically: <strong>{nextId}</strong></p>
            </div>
            {error && <p className="error">{error}</p>}
            <div className="wizard-buttons">
              <button className="btn btn-primary" onClick={saveSwitch}>
                💾 Save Switch
              </button>
              <button className="btn btn-secondary" onClick={onCancel}>
                Cancel
              </button>
            </div>
          </div>
        );

      case WIZARD_STEPS.COMPLETE:
        return (
          <div className="wizard-step">
            <h3>✅ Switch Added!</h3>
            <div className="success-message">
              <p><strong>{switchName}</strong> has been added successfully.</p>
              <div className="codes-summary">
                <div className="captured-code success">ON Code: <code>{onCode}</code></div>
                <div className="captured-code success">OFF Code: <code>{offCode}</code></div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="wizard-overlay">
      <div className="wizard-modal">
        <button className="wizard-close" onClick={onCancel}>×</button>
        {renderContent()}
      </div>
    </div>
  );
}

export default AddSwitchWizard;
