FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./ 
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy source
COPY . .

# Build Next.js app
RUN npm run build

# Production runtime image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app ./

EXPOSE 3000

CMD ["npm", "run", "start"]


