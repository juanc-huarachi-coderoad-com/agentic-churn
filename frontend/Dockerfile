FROM node:20-alpine AS builder

# Pinned to match the version this project was scaffolded with (frontend/package.json has
# no packageManager field to pin it automatically) — corepack's default "latest" resolves
# to a pnpm release requiring Node >= 22, incompatible with node:20-alpine.
RUN corepack enable && corepack prepare pnpm@10.28.2 --activate

WORKDIR /app

# Dependencies first, so a source-only change doesn't invalidate this layer.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
