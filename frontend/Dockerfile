# GliHub 3.0 Vue 3.5 + Vite 6 Multi-Arch Frontend Image
FROM node:24-alpine AS builder
WORKDIR /build
COPY package.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build:prod

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
