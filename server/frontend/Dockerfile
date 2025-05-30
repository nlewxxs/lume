FROM node:18-alpine

WORKDIR /app

# Copy the whole dashboard application
COPY frontend/lume-dashboard/ .
WORKDIR /app/lume-dashboard

# Install dependencies, including Vite
RUN npm install
RUN npm install -D autoprefixer @tailwindcss/vite concurrently
RUN npm install lucide-react

# Expose the ports for Redis and the WS server
EXPOSE 5173  
EXPOSE 4000

# Start npm server with Vite
CMD ["npm", "run", "start:docker"]


