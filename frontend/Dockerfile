FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --silent || true
COPY . .
CMD ["npm", "run", "dev"]
