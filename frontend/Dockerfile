# Stage 1: Build Vite React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications and install cleanly
COPY package*.json ./
RUN npm ci

# Copy application source code
COPY . .

# Set relative API base URL for same-origin proxy
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production bundle
RUN npm run build

# Stage 2: Serve via Caddy web server
FROM caddy:2-alpine

WORKDIR /srv

# Copy built frontend assets
COPY --from=builder /app/dist /srv

# Copy Caddy configuration and entrypoint
COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /entrypoint.sh

# Ensure default auth file exists and entrypoint is executable
RUN touch /etc/caddy/auth.caddy && \
    chmod +x /entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
