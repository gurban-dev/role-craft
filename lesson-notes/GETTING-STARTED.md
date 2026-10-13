## Start the Application with Docker

Docker Compose builds the required container images and starts the services defined in `compose.yaml` or `docker-compose.yml`. The `--build` option tells Docker Compose to build the images before starting the services.

### Linux

```bash
docker compose up --build
```

- **`docker compose up --build`** builds the required images and starts the services defined in the Compose configuration.

### Windows

Open PowerShell in the project directory.

#### 1. Create the environment file

```powershell
Copy-Item .env.example .env
```

This command copies `.env.example` to a new file named `.env`.

The example file provides the environment variable names and default values expected by the application. The `.env` file is used to configure environment-specific settings, such as database credentials, API keys, and application secrets.

Open `.env` and replace placeholder values with the required configuration. Do not commit real secrets to version control.

#### 2. Build and start the application

```powershell
docker compose up --build
```

This command builds the required Docker images and starts the services defined in the Compose configuration.

Docker Compose reads the configuration and environment variables it needs to configure the services. If the Compose file references variables from `.env`, those values are used when configuring the containers.

### What to Expect

After the command finishes starting the services, Docker Compose displays their logs in the terminal. Keep the terminal open while you want to monitor the logs and run the services in the foreground.

To stop the services, press `Ctrl+C`. To stop and remove the containers created by Compose, run:

```bash
docker compose down
```

This removes the containers and associated Compose network, but does not normally delete named volumes, such as those used to persist database data.