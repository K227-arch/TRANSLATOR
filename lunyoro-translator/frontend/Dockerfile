FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
# Remove Windows-only native binaries from package.json before installing.
# They are locked to win32 and will never resolve on Linux — the Linux
# equivalents (@tailwindcss/oxide, lightningcss) are already in devDependencies.
RUN node -e " \
  const fs = require('fs'); \
  const pkg = JSON.parse(fs.readFileSync('package.json')); \
  const winPkgs = ['@tailwindcss/oxide-win32-x64-msvc','lightningcss-win32-x64-msvc']; \
  winPkgs.forEach(p => { delete pkg.dependencies[p]; }); \
  fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2)); \
  console.log('Removed Windows-only native packages from package.json'); \
"
# Use npm install (not ci) so npm resolves platform-correct binaries on Linux
RUN npm install --prefer-offline 2>&1 | tail -5

COPY . .

# Build arg passed at build time: docker build --build-arg NEXT_PUBLIC_API_URL=https://api.yourdomain.com
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV DOCKER_BUILD=1

RUN npm run build

# ── Production image ──────────────────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
