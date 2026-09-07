# Docker Deployment Procedure

This project runs as one Streamlit container and uses MongoDB Atlas as its
external database. The container does not contain Atlas credentials; secrets
are injected at runtime through `.env` or the hosting provider's secret store.

## Prerequisites

- Docker Desktop 4.x or Docker Engine with Compose v2
- A MongoDB Atlas M0 cluster and a least-privilege database user
- Python installed locally only for the ETL/ML jobs
- A rotated HealthSentinel admin password hash

Check Docker before starting:

```powershell
docker --version
docker compose version
docker info
```

If `docker info` cannot connect to the engine, start Docker Desktop first.

## Atlas preparation

1. Create an Atlas M0 cluster and a database user with read/write access only
   to the `healthsentinel` database.
2. Configure Atlas Network Access for the deployment host. Avoid
   `0.0.0.0/0` unless the database user has a strong rotated password.
3. Copy `.env.example` to `.env` and set `MONGO_URI`. Never commit `.env`.
4. Verify and publish raw plus cleaned collections:

   ```powershell
   python etl/sync_atlas_pipeline.py --dry-run
   python etl/sync_atlas_pipeline.py
   ```

5. Verify the login hashes locally:

   ```powershell
   python -m src.admin_auth check
   ```

For a hosted container, provide `ADMIN_HASHES_JSON` through the platform
secret store. The value is a JSON object mapping usernames to the scrypt hash
stored in `data/.admin_hashes.csv`; do not put plaintext passwords in it.

## Local Docker

```powershell
docker compose build --pull
docker compose up -d
docker compose ps
```

Open `http://localhost:8501`. The container health endpoint is
`http://localhost:8501/_stcore/health`.

Useful operations:

```powershell
docker compose logs -f healthsentinel
docker compose restart healthsentinel
docker compose down
```

The database remains in Atlas when the container stops; `docker compose down`
does not delete Atlas data.

## Updating the deployment

Pull the new project version, rebuild, and recreate the container:

```powershell
docker compose build --pull
docker compose up -d --force-recreate
docker compose ps
```

If the new image is unhealthy, inspect logs and return to the previous image
tag. Do not remove the working image until the new container passes the health
check and login test.

## Streamlit Community Cloud

1. Push the project without `.env`, `data/.admin_hashes.csv`, or raw exports.
2. Create an app using `app.py` and `requirements.txt`.
3. Add these values in the Streamlit Secrets panel:

   ```toml
   MONGO_URI = "mongodb+srv://..."
   MONGO_DB = "healthsentinel"
   ADMIN_HASHES_JSON = '{"username":"scrypt$..."}'
   ```

4. Add the deployment network to Atlas Network Access.
5. Confirm the login screen appears before dashboard content.

## Docker host or Hugging Face Spaces

Inject secrets at runtime; do not bake them into the image:

```bash
docker build -t healthsentinel .
docker run --rm -p 8501:8501 --env-file .env healthsentinel
```

For a persistent service, add a restart policy and a named image tag:

```bash
docker run -d --name healthsentinel --restart unless-stopped \
   -p 8501:8501 --env-file .env healthsentinel:local
```

For scheduled refreshes, run the ETL and ML jobs in a protected job:

```bash
python etl/sync_atlas_pipeline.py
python -m src.ml_pipeline
```

## Post-deployment verification

Check `/_stcore/health`, authenticate with a rotated account, open each page,
and confirm dashboards report Atlas data rather than CSV fallback warnings.
Run the ETL a second time and verify that its logs show updates rather than
duplicate inserts. Confirm that `.env` is not inside the image or source
repository:

```powershell
docker run --rm healthsentinel:local sh -c "test ! -e /app/.env"
```

The Dockerfile runs the app as an unprivileged `appuser`; the health check,
XSRF protection, and headless server settings are enabled by default.