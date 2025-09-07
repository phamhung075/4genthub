# Optimized Frontend Dockerfile with minimal size

# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app
# Copy only package files
COPY dhafnck-frontend/package*.json ./
# Clean install with frozen lockfile and production flag
RUN npm ci --only=production --silent && \
    npm cache clean --force

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /app
# Copy package files and install all deps (including dev)
COPY dhafnck-frontend/package*.json ./
RUN npm ci --silent && \
    npm cache clean --force
# Copy source and build
COPY dhafnck-frontend/ ./
# Build with production optimizations
ENV NODE_ENV=production
RUN npm run build && \
    rm -rf node_modules src public *.json *.js *.ts

# Stage 3: Runtime - Ultra-light nginx
FROM nginx:stable-alpine AS runtime

# Remove default nginx stuff we don't need
RUN rm -rf /usr/share/nginx/html/* \
    /etc/nginx/conf.d/default.conf \
    /docker-entrypoint.d/* && \
    # Create nginx user if not exists
    adduser -D -H -u 1000 -s /sbin/nologin nginx 2>/dev/null || true && \
    # Optimize nginx directories
    mkdir -p /var/cache/nginx /var/log/nginx /var/run && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run && \
    # Remove unnecessary nginx modules
    rm -f /etc/nginx/modules/*.conf

# Copy optimized nginx config
COPY --from=builder /app/build /usr/share/nginx/html

# Create optimized nginx config
RUN cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes 1;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 512;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml application/atom+xml image/svg+xml 
               text/x-js text/x-cross-domain-policy application/x-font-ttf 
               application/x-font-opentype application/vnd.ms-fontobject 
               image/x-icon;
    
    # Cache control
    map $sent_http_content_type $expires {
        default                    off;
        text/html                  epoch;
        text/css                   max;
        application/javascript     max;
        ~image/                    max;
        ~font/                     max;
    }
    
    # Logging (minimal)
    access_log off;
    
    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        
        # Cache control
        expires $expires;
        
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        # API proxy with caching
        location /api {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
            proxy_buffering off;
            proxy_request_buffering off;
            
            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }
        
        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Set correct permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Switch to non-root user
USER nginx

EXPOSE 80

# Use exec form for better signal handling
CMD ["nginx", "-g", "daemon off;"]