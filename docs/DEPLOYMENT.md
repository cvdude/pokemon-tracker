# Synology Container Manager deployment

EvoDeck runs as a production Gunicorn container on port `8080`. Its SQLite database is not included in the image: the compose file mounts the NAS database directory at `/app/database`, so `pokemon.db` survives image rebuilds and container replacement.

## NAS setup

1. Install **Container Manager** on the DS920+.
2. Place the repository at `/volume1/web/pokemon-tracker`.
3. Confirm the live database exists at `/volume1/web/pokemon-tracker/database/pokemon.db` and that Container Manager can read and write the directory.
4. In Container Manager, create a Project from the repository folder and select `docker-compose.yml`.
5. Build and start the project. Container Manager creates a container named `evodeck` and maps NAS port `8080` to container port `8080`.
6. Open `http://<NAS-IP>:8080/`.

## Runtime behavior

- The container uses Python 3.9, Flask, and Gunicorn; it does not run Flask’s development server.
- Gunicorn binds to `0.0.0.0:8080` with two workers and four threads per worker.
- `restart: unless-stopped` restores the service after a NAS restart unless it was explicitly stopped.
- The healthcheck requests `http://127.0.0.1:8080/` inside the container every 30 seconds.
- `/volume1/web/pokemon-tracker/database` is bind-mounted to `/app/database`. Do not replace or delete this host directory during rebuilds.

## Updating

1. Back up `database/pokemon.db` using the existing NAS backup process.
2. Pull the updated repository files into `/volume1/web/pokemon-tracker`.
3. In Container Manager, rebuild and restart the `evodeck` project.
4. Confirm the container is healthy, then load the dashboard and a set page.

The tracked `database/schema_v0.sql` remains a schema reference. The live `database/pokemon.db` is intentionally ignored by Git and is retained by the bind mount.
