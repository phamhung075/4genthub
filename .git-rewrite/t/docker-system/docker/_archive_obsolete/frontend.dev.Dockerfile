# Development stage with hot reload
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files from the frontend directory
COPY dhafnck-frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy all frontend files
COPY dhafnck-frontend/ ./

# Expose Vite dev server port
EXPOSE 3000

# Start React dev server with hot reload
CMD ["npm", "start"]