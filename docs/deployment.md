# Deployment

## Docker

```bash
# API only
docker compose up

# API + Dagster orchestration UI
docker compose --profile orchestration up
```

## GCP Cloud Run

```bash
gcloud builds submit --config cloudbuild.yaml
```

`cloudbuild.yaml` builds the Docker image, pushes to Artifact Registry, deploys
the API service (`hit-prompt-engine`) and updates the weekly batch job
(`hit-engine-weekly-ingest`).

## Manual

```bash
pip install -r requirements.txt
python run_pipeline.py serve --host 0.0.0.0 --port 8000
```
