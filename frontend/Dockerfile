# ── Build Stage ──
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for better Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files
COPY . .

# Build argument for API URL (defaults to /api for reverse-proxied deployment)
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Production Stage ──
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
