# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Build arguments
ARG VITE_API_URL=/api/v1

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN VITE_API_URL=${VITE_API_URL} npm run build

# Runtime stage - serve with nginx
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]