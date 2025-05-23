import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Power, Settings, RefreshCw, Send, X } from 'lucide-react';

function App() {
  // State management
  const [isLoaded, setIsLoaded] = useState(false);
  const [inputData, setInputData] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [metrics, setMetrics] = useState({
    temperature: 25.4,
    pressure: 1013.25,
    voltage: 12.0,
    current: 2.3,
    uptime: '00:15:42',
    lastUpdate: new Date().toLocaleTimeString()
  });
  const [warnings, setWarnings] = useState([]);
  const [logs, setLogs] = useState([]);
  
  // Refs for simulated Redis connection
  const redisSimulator = useRef(null);
  const metricsInterval = useRef(null);

  // Simulated Redis connection and subscription
  useEffect(() => {
    // Set loaded state after a brief delay to ensure CSS is applied
    setTimeout(() => setIsLoaded(true), 100);
    
    // Simulate Redis connection
    setConnectionStatus('connecting');
    
    setTimeout(() => {
      setConnectionStatus('connected');
      addLog('Connected to Redis server');
      addLog('Subscribed to "input_data" topic');
    }, 1000);

    // Simulate incoming data on "input_data" topic
    const dataInterval = setInterval(() => {
      if (Math.random() > 0.8) { // 20% chance of receiving data
        const mockData = {
          sensor_id: Math.floor(Math.random() * 5) + 1,
          value: (Math.random() * 100).toFixed(2),
          timestamp: new Date().toISOString()
        };
        addLog(`Received on input_data: ${JSON.stringify(mockData)}`);
        
        // Simulate warning conditions
        if (parseFloat(mockData.value) > 85) {
          showWarning(`High sensor value detected: ${mockData.value}`);
        }
      }
    }, 3000);

    // Update metrics periodically
    metricsInterval.current = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        temperature: (25 + Math.random() * 10).toFixed(1),
        pressure: (1010 + Math.random() * 10).toFixed(2),
        voltage: (11.8 + Math.random() * 0.4).toFixed(1),
        current: (2.0 + Math.random() * 0.6).toFixed(1),
        lastUpdate: new Date().toLocaleTimeString()
      }));
    }, 2000);

    return () => {
      clearInterval(dataInterval);
      if (metricsInterval.current) {
        clearInterval(metricsInterval.current);
      }
    };
  }, []);

  // Utility functions
  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-9), `[${timestamp}] ${message}`]);
  };

  const showWarning = (message) => {
    const warning = {
      id: Date.now(),
      message,
      timestamp: new Date().toLocaleTimeString()
    };
    setWarnings(prev => [...prev, warning]);
    
    // Auto-remove warning after 5 seconds
    setTimeout(() => {
      setWarnings(prev => prev.filter(w => w.id !== warning.id));
    }, 5000);
  };

  const publishToRedis = (data) => {
    const payload = {
      data,
      timestamp: new Date().toISOString(),
      source: 'dashboard'
    };
    addLog(`Published to output_data: ${JSON.stringify(payload)}`);
  };

  // Button handlers
  const handleStartOperation = () => {
    publishToRedis({ command: 'start_operation' });
    addLog('Start operation command sent');
  };

  const handleStopOperation = () => {
    publishToRedis({ command: 'stop_operation' });
    addLog('Stop operation command sent');
  };

  const handleEmergencyStop = () => {
    publishToRedis({ command: 'emergency_stop' });
    addLog('EMERGENCY STOP activated');
    showWarning('Emergency stop activated!');
  };

  const handleReset = () => {
    publishToRedis({ command: 'reset_system' });
    addLog('System reset command sent');
  };

  const handleSendData = () => {
    if (inputData.trim()) {
      publishToRedis({ custom_data: inputData });
      addLog(`Custom data sent: "${inputData}"`);
      setInputData('');
    }
  };

  const handleCalibrate = () => {
    publishToRedis({ command: 'calibrate_sensors' });
    addLog('Sensor calibration initiated');
  };

  const dismissWarning = (warningId) => {
    setWarnings(prev => prev.filter(w => w.id !== warningId));
  };

  return (
    <div className={`min-h-screen bg-gray-900 text-white p-6 transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">LUME</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500' : 
              connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
            }`}></div>
            <span className="text-sm">Redis: {connectionStatus}</span>
          </div>
          <div className="text-sm text-gray-400">
            Last Update: {metrics.lastUpdate}
          </div>
        </div>
      </div>

      {/* Warning Popups */}
      {warnings.map(warning => (
        <div key={warning.id} className="fixed top-4 right-4 bg-red-600 text-white p-4 rounded-lg shadow-lg z-50 max-w-sm">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold">Warning</div>
              <div className="text-sm">{warning.message}</div>
              <div className="text-xs text-red-200 mt-1">{warning.timestamp}</div>
            </div>
            <button 
              onClick={() => dismissWarning(warning.id)}
              className="text-red-200 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Control Panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Operation Controls */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Operation Controls</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <button 
                onClick={handleStartOperation}
                className="bg-green-600 hover:bg-green-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Power className="w-5 h-5" />
                Start
              </button>
              <button 
                onClick={handleStopOperation}
                className="bg-gray-600 hover:bg-gray-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Power className="w-5 h-5" />
                Stop
              </button>
              <button 
                onClick={handleEmergencyStop}
                className="bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <AlertTriangle className="w-5 h-5" />
                E-Stop
              </button>
              <button 
                onClick={handleReset}
                className="bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
                Reset
              </button>
              <button 
                onClick={handleCalibrate}
                className="bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Settings className="w-5 h-5" />
                Calibrate
              </button>
            </div>
          </div>

          {/* Data Input */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Data Input</h2>
            <div className="flex gap-4">
              <input
                type="text"
                value={inputData}
                onChange={(e) => setInputData(e.target.value)}
                placeholder="Enter data to send..."
                className="flex-1 bg-gray-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && handleSendData()}
              />
              <button
                onClick={handleSendData}
                disabled={!inputData.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg flex items-center gap-2 transition-colors"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </div>
          </div>

          {/* Activity Log */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Activity Log</h2>
            <div className="bg-gray-900 rounded-lg p-4 h-48 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="text-gray-500 text-sm">No activity yet...</div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="text-sm text-gray-300 mb-1 font-mono">
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Metrics Panel */}
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Metrics</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Temperature</span>
                <span className="text-lg font-mono">{metrics.temperature}°C</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Pressure</span>
                <span className="text-lg font-mono">{metrics.pressure} hPa</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Voltage</span>
                <span className="text-lg font-mono">{metrics.voltage}V</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Current</span>
                <span className="text-lg font-mono">{metrics.current}A</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Uptime</span>
                <span className="text-lg font-mono">{metrics.uptime}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Status</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm">System Online</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-sm">Sensors Active</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <span className="text-sm">Calibration Due</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
