import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Power, RefreshCw, X, Wifi, WifiOff, Joystick} from 'lucide-react';

function App() {
    // State management
    const [droneConnStatus, setDroneConnStatus] = useState('disconnected');
    const [lastUpdate, setLastUpdate] = useState(new Date().toLocaleTimeString());
    const [flightMode, setFlightMode] = useState('gesture');
    const [controllerConnStatus, setControllerConnStatus] = useState('disconnected');
    const [warnings, setWarnings] = useState([]);
    const [errors, setErrors] = useState([]);
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        let ws;
        let retryTimeout;

        const connectWebSocket = () => {
            console.log("Attempting to initialise websocket connection");
            ws = new WebSocket(`ws://${window.location.hostname}:4000`);

            ws.onopen = () => {
                console.log('✅ WebSocket connected');
            };

            ws.onmessage = event => {
                const data = JSON.parse(event.data);
                console.log("Received WS message of type: ", data.type);
                setLastUpdate(new Date().toLocaleTimeString());
                if (data.type === "ESTOP") {
                    // Trigger ESTOP if not already in estop
                    if (flightMode != 'estop') {
                        setFlightMode('estop');
                        addLog("Emergency stop triggered");
                        showError("CONTROLLER TRIGGERED ESTOP");
                    }
                } else if (data.type == "controller_status") {
                    // update the controller status on screen
                    setControllerConnStatus(data.value);
                    if (data.value == "disconnected") {
                        addLog("Controller disconnected");
                        showWarning("Controller disconnected.");
                    } else if (data.value == "hardware_failure") {
                        addLog("Controller reported hardware failure");
                        showError("Hardware Failure - Check MPU wiring");
                    }
                } else if (data.type == "drone_status") {
                    // update the drone status on screen
                    setDroneConnStatus(data.value);
                    if (data.value == "disconnected") {
                        addLog("Drone disconnected");
                        showWarning("Drone disconnected.");
                    }
                } else if (data.type == "flight_mode") {
                    // update the drone status on screen
                    addLog(`Flight mode changed to ${data.value}`);
                    setFlightMode(data.value);
                }
            };

            ws.onerror = err => {
                console.error('❌ WebSocket error:', err);
            };

            ws.onclose = () => {
                console.warn('⚠️ WebSocket closed, retrying in 1s...');
                retryTimeout = setTimeout(connectWebSocket, 1000);
            };
        };

        connectWebSocket();

        return () => {
            clearTimeout(retryTimeout);
            if (ws) ws.close();
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

    const showError = (message) => {
        const error = {
            id: Date.now(),
            message,
            timestamp: new Date().toLocaleTimeString()
        };
        setErrors(prev => [...prev, error]);
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
        showError('Triggered server side')
    };

    const handleReset = () => {
        publishToRedis({ command: 'reset_system' });
        addLog('System reset command sent');
    };

    const handleCalibrate = () => {
        publishToRedis({ command: 'calibrate_sensors' });
        addLog('Sensor calibration initiated');
    };

    const toggleFlightMode = () => {
        if (flightMode !== 'estop') {
            if (flightMode === 'gesture') {
                setFlightMode('manual');
            } else {
                setFlightMode('gesture');
            }
        }
    };

    const dismissWarning = (warningId) => {
        setWarnings(prev => prev.filter(w => w.id !== warningId));
    };

    const dismissError = (errorId) => {
        setErrors(prev => prev.filter(w => w.id !== errorId));
    };

    return (
        <div className={`min-h-screen bg-gray-900 text-white p-6`}>
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">LUME</h1>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded-full ${navigator.onLine ? 'bg-green-500' : 'bg-red-500'
                            }`}></div>
                        <span className="text-sm text-gray-400">Network - {navigator.onLine ? 'Connected' : 'Disconnected'}</span>
                        {navigator.onLine ? <Wifi className="w-4 h-4 text-gray-400" /> : <WifiOff className="w-4 h-4 text-gray-400" />}
                    </div>
                </div>
            </div>

            {/* Warning Popups */}
            {warnings.map(warning => (
                <div key={warning.id} className="fixed bottom-4 right-4 bg-red-600 text-white p-4 rounded-lg shadow-lg z-50 max-w-sm">
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


            {/* Critical Error Popups */}
            {errors.map(error => (
                <div
                    key={error.id}
                    className="fixed left-20 right-20 top-50 bottom-50 z-50 rounded-3xl border-4 border-red-500 flex items-center justify-center bg-[rgba(255,28,28,0.9)] text-white p-8"
                >
                    <div className="text-center max-w-3xl">
                        <div className="text-6xl font-extrabold mb-4 flex justify-center items-center gap-4">
                            <AlertTriangle className="w-12 h-12" />
                            CRITICAL ERROR
                        </div>
                        <div className="text-4xl mb-2">{error.message}</div>
                        <div className="text-xl text-red-200 mb-6">{error.timestamp}</div>
                        <button
                            onClick={() => dismissError(error.id)}
                            className="mt-4 px-6 py-3 bg-white text-red-700 text-xl font-bold rounded-lg hover:bg-red-100 transition"
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            ))}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Control Panel */}
                <div className="lg:col-span-2 space-y-6">


                    {/* Activity Log */}
                    <div className="bg-gray-800 rounded-lg p-6">
                        <h2 className="text-xl font-semibold mb-4">Activity Log</h2>
                        <div className="bg-gray-900 rounded-lg p-4 bottom-4 overflow-y-auto">
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

                <div className="space-y-6">
                    <div className="bg-gray-800 rounded-lg p-6">
                        <button
                            onClick={toggleFlightMode}
                            className={`w-full ${flightMode === 'gesture' ? 'bg-cyan-500' : 'bg-purple-500'} ${flightMode === 'gesture' ? 'hover:bg-cyan-700' : 'hover:bg-purple-700'} text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors`}
                        >
                            Operation mode: {flightMode === 'gesture' ? 'Gesture detection' : 'Manual control'}
                        </button>
                    </div>
                    {/* Metrics Panel */}
                    <div className="space-y-6">
                        <div className="bg-gray-800 rounded-lg p-6">
                            <h2 className="text-xl font-semibold mb-4">System Status</h2>
                            <div className="space-y-3">
                                <div className="space-y-1">
                                                                        <div className="flex items-center gap-2">
                                        <div className={`w-4 h-4 rounded-full ${droneConnStatus === 'connected' ? 'bg-green-500' :
                                            droneConnStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
                                            }`}></div>
                                        <span className="text-lg">Drone - </span>
                                        <span className="text-lg text-gray-400">{droneConnStatus}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className={`w-4 h-4 rounded-full ${controllerConnStatus === 'connected' ? 'bg-green-500' :
                                            controllerConnStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
                                            }`}></div>
                                        <span className="text-lg">Controller - </span>
                                        <span className="text-lg text-gray-400">{controllerConnStatus}</span>
                                    </div>
                                </div>
                                <div className="text-sm text-gray-400">
                                    Last Update: {lastUpdate}
                                </div>
                            </div>
                        </div>
                    </div>

                    
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
                                className="col-span-2 bg-yellow-500 hover:bg-yellow-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                                <Joystick className="w-5 h-5" />
                                Manual Override
                            </button>
                        </div>
                    </div>


                </div>
            </div>
        </div>
    );
}

export default App;
