# Build stage
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files from the frontend directory
COPY dhafnck-frontend/package*.json ./

# Clear npm cache and install all dependencies
RUN npm cache clean --force && \
    npm ci

# Copy all frontend files
COPY dhafnck-frontend/ ./

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration from the frontend directory
COPY dhafnck-frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (internal to container)
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]