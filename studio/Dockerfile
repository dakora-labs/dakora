FROM node:20-alpine AS builder

WORKDIR /app

# Accept API URL as build argument
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Accept Clerk Publishable Key as build argument
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

# Accept Authentication enabled flag as build argument
ARG VITE_AUTH_REQUIRED
ENV VITE_AUTH_REQUIRED=$VITE_AUTH_REQUIRED

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]