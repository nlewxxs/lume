FROM node:18-alpine

WORKDIR /app

# Copy the whole dashboard application
COPY frontend/lume-dashboard/ .
WORKDIR /app/lume-dashboard

# Install dependencies, including Vite
RUN npm install
RUN npm install -D tailwindcss postcss autoprefixer @tailwindcss/vite
RUN npm install lucide-react

# Expose the port
EXPOSE 5173

# Start npm server with Vite
CMD ["npm", "run", "dev"]


