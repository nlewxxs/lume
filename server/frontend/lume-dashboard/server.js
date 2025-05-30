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

// Subscribe to a Redis channel
redisSubscriber.subscribe('ESTOP');

redisSubscriber.on('message', (channel, message) => {
  // Broadcast message to all connected WS clients
  console.log("Express server received ESTOP through ioredis");
  wss.clients.forEach(client => {
    if (client.readyState === 1) {
      console.log("Publishing ESTOP through websocket...");
      client.send(message);
    }
  });
});

wss.on('connection', ws => {
  console.log('✅ WebSocket client connected');
});

app.use(express.json());

// app.post('/api/publish', async (req, res) => {
  // const { message } = req.body;
  // await redisPublisher.publish('my-channel', message);
  // res.json({ success: true });
// });

server.listen(4000, () => {
  console.log('Server listening on port 4000');
});

