# Installs the Swag Labs (saucedemo) web app from its public source code,
# the way a release would be installed on a customer machine.
FROM node:24-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG REF=main
RUN git clone --depth 1 --branch ${REF} https://github.com/saucelabs/sample-app-web.git /app
WORKDIR /app
RUN npm ci && npm run build

FROM node:24-slim
WORKDIR /app
COPY --from=build /app /app
EXPOSE 3000
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "3000", "--strictPort"]
