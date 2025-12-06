# Build stage
FROM node:22-alpine AS build

WORKDIR /app

# Build arguments for Vite environment variables
ARG VITE_API_BASE_URL
ARG VITE_API_URL
ARG VITE_ENABLE_BASIC_LOGIN=true
ARG VITE_TELEGRAM_BOT_USERNAME

# Set environment variables for Vite build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_ENABLE_BASIC_LOGIN=${VITE_ENABLE_BASIC_LOGIN}
ENV VITE_TELEGRAM_BOT_USERNAME=${VITE_TELEGRAM_BOT_USERNAME}

# Copy package files
COPY package.json package-lock.json ./

# Install ALL dependencies (including devDependencies for build tools)
# Use --ignore-scripts to skip native module compilation that we don't need
RUN npm ci --legacy-peer-deps --ignore-scripts

COPY . .

RUN npm run build

# Production stage
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
