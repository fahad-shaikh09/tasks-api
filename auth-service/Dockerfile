# ============================================================
# Auth Service Dockerfile (OpenShift / CRC)
#
# Node.js + better-auth + Express. Owns users + sessions in
# the shared Postgres (better-auth manages its own tables).
#
# Build:
#   oc new-build --binary --strategy=docker --name=auth-service -n tasks-app
#   oc start-build auth-service --from-dir=auth-service --follow -n tasks-app
# ============================================================

FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
# No lockfile — install resolves at build time.
RUN npm install --include=dev

COPY tsconfig.json ./
COPY src ./src

RUN npm run build

# =========================
# Runtime stage
# =========================
FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production

COPY package.json ./
RUN npm install --omit=dev && npm cache clean --force

COPY --from=builder /app/dist ./dist
COPY public ./public

# OpenShift assigns a random UID — make the project group-writable.
RUN chgrp -R 0 /app && chmod -R g=u /app

EXPOSE 8003

CMD ["node", "dist/server.js"]
