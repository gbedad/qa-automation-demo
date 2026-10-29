# Installs the restful-booker API from its public source code.
FROM node:24-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG REF=main
RUN git clone --depth 1 --branch ${REF} https://github.com/mwinteringham/restful-booker.git /app
WORKDIR /app
RUN npm install --omit=dev
EXPOSE 3001
CMD ["npm", "start"]
