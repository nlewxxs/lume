// express server for performing Redis functionality in backend
import express from 'express';
import Redis from 'ioredis';
import { WebSocketServer } from 'ws';
import http from 'http';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

let last_controller_status = null;
let last_drone_status = null;
let last_flight_mode = null;

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
  password: process.env.REDIS_PASSWORD || undefined,
});

const redisPublisher = new Redis({
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
  password: process.env.REDIS_PASSWORD || undefined,
});

const redisSubscriber = new Redis({
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
  password: process.env.REDIS_PASSWORD || undefined,
});

setInterval(async () => {
    try {
        const new_controller_status = await redis.get('controller_status');
        if (new_controller_status !== last_controller_status) {
            wss.clients.forEach(client => {
                if (client.readyState === 1) {
                    console.log("Updating controller status...");
                    client.send(JSON.stringify({type: 'controller_status', value: new_controller_status}));
                }
            });

            last_controller_status = new_controller_status;
        }
    } catch (err) {
        console.log("Redis polling error: ", err);
    }
}, 1000); // Poll every second

setInterval(async () => {
    try {
        const new_drone_status = await redis.get('drone_status');
        if (new_drone_status !== last_drone_status) {
            wss.clients.forEach(client => {
                if (client.readyState === 1) {
                    console.log("Updating drone status...");
                    client.send(JSON.stringify({type: 'drone_status', value: new_drone_status}));
                }
            });

            last_drone_status = new_drone_status;
        }
    } catch (err) {
        console.log("Redis polling error: ", err);
    }
}, 1000); // Poll every second

setInterval(async () => {
    try {
        const new_flight_mode = await redis.get('flight_mode');
        if (new_flight_mode !== last_flight_mode) {
            wss.clients.forEach(client => {
                if (client.readyState === 1) {
                    console.log("Updating flight mode status...");
                    client.send(JSON.stringify({type: 'flight_mode', value: new_flight_mode}));
                }
            });

            last_flight_mode = new_flight_mode;
        }
    } catch (err) {
        console.log("Redis polling error: ", err);
    }
}, 200); // Poll 5 times every second


// Subscribe to ESTOP channel
redisSubscriber.subscribe('ESTOP');

redisSubscriber.on('message', (channel, message) => {
    // Broadcast message to all connected WS clients
    console.log("Express server received ESTOP through ioredis");
    wss.clients.forEach(client => {
        if (client.readyState === 1) {
            console.log("Publishing ESTOP through websocket...");
            // forward the value
            client.send(JSON.stringify({ type: "ESTOP", value: {message} }));
        }
    });
});


wss.on('connection', ws => {
    console.log('✅ WebSocket client connected');
    ws.on('message', (msg) => {
        let message = JSON.parse(msg);
        console.log("Received message from frontend:", message);
        if (message.type == "flight_mode") {
            console.log('Received flight mode update');
            redis.set('flight_mode', message.value);
        } else if (message.type == "keypress") {
            if (message.value == "ArrowLeft") {
                redis.set('remote_command', 'left');
            } else if (message.value == "ArrowRight") {
                redis.set('remote_command', 'right');
            } else if (message.value == "ArrowUp") {
                redis.set('remote_command', 'forward');
            } else if (message.value == "ArrowDown") {
                redis.set('remote_command', 'back');
            } else if (message.value == "]") {
                redis.set('remote_command', 'up');
            } else if (message.value == "#") {
                redis.set('remote_command', 'down');
            } else if (message.value == "t" || message.value == "T") {
                redisPublisher.publish('remote_takeoff_land', "takeoff");
            } else if (message.value == "l" || message.value == "L") {
                redisPublisher.publish('remote_takeoff_land', "land");
            }
        } else if (message.type == "keyunpress") {
            // clear the remote command
            redis.set('remote_command', '');
        } else {
            console.error("Error: Unknown message type received in websocket!")
        }
    });
});


app.use(express.json());

server.listen(4000, () => {
  console.log('Server listening on port 4000');
});

