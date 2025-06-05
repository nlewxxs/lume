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
                    console.log("Updating drone status...");
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
            // No need to send a value
            client.send(JSON.stringify({ type: "ESTOP" }));
        }
    });
});


wss.on('connection', ws => {
  console.log('✅ WebSocket client connected');
});

app.use(express.json());

server.listen(4000, () => {
  console.log('Server listening on port 4000');
});

