#!/usr/bin/env bash
#
# gcloud_command.sh — deploy and schedule this project on GCP.
#
#   ./gcloud_command.sh all        # everything, in order (first-time setup)
#   ./gcloud_command.sh bootstrap  # enable APIs, upload your key to Secret Manager
#   ./gcloud_command.sh api        # redeploy the API only
#   ./gcloud_command.sh web        # redeploy the web app only
#   ./gcloud_command.sh scheduler  # (re)create the Cloud Scheduler jobs only
#   ./gcloud_command.sh urls       # print the deployed URLs
#
# This deploys straight from source with `gcloud run deploy --source`.
#
# Before running: put your service account key at ./gcp-key.json, or run with
#   LOCAL_KEY_FILE=/path/to/key.json ./gcloud_command.sh all

set -euo pipefail

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROJECT_ID="festival-smoke-detector"
REGION="us-west1"                       # keep the same region everywhere
RUNTIME_SERVICE_ACCOUNT="festival-smoke@${PROJECT_ID}.iam.gserviceaccount.com"

BUCKET_NAME="festival-smoke-detector-data"   # <-- SET THIS to your real bucket

API_SERVICE="api-server"                # Cloud Run service name for the API
WEB_SERVICE="webapp"                    # Cloud Run service name for Streamlit

API_DIR="./api"                         # folder holding the API Dockerfile
WEB_DIR="./streamlit"                   # folder holding the Streamlit Dockerfile

API_PORT=8000                           # must match EXPOSE/CMD in api/Dockerfile
WEB_PORT=8501                           # Streamlit default

LOCAL_KEY_FILE="${LOCAL_KEY_FILE:-./gcp-key.json}"

# The code reads GCP_SERVICE_ACCOUNT_KEY as a file path, so the secret is
# mounted and that variable points at the mount.
GCP_KEY_SECRET="group-hw3-gcp-key"
SECRET_MOUNT_PATH="/run/secrets/gcp_key"

SCHEDULE="0 0 * * *"                    # collection, nightly
TRANSFORM_SCHEDULE="0 2 * * *"          # transform, after collection finishes
SCHEDULER_TZ="America/Los_Angeles"
MESSAGE_BODY='{}'

# Must match the @app.post path in main.py. If your route is /transform,
# change this.
TRANSFORM_PATH="/extract_and_save"

# EPA pulls ~150 MB across 27 years, and the transform holds it in pandas.
RUN_TIMEOUT=1800
RUN_MEMORY=2Gi
SCHEDULER_DEADLINE=1800s
# ──────────────────────────────────────────────────────────────────────────────

# ─── validation ───────────────────────────────────────────────────────────────
for _var in PROJECT_ID REGION BUCKET_NAME API_SERVICE WEB_SERVICE API_DIR \
            WEB_DIR API_PORT WEB_PORT LOCAL_KEY_FILE GCP_KEY_SECRET \
            SECRET_MOUNT_PATH SCHEDULE TRANSFORM_PATH; do
  if [ -z "${!_var}" ]; then
    echo "ERROR: $_var is empty -- fill in the CONFIG block at the top of" \
         "this script before running it." >&2
    exit 1
  fi
done
unset _var

if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
  echo "ERROR: PROJECT_ID is still the placeholder. Edit the CONFIG block." >&2
  exit 1
fi
if [ ! -f "$LOCAL_KEY_FILE" ]; then
  echo "ERROR: LOCAL_KEY_FILE '$LOCAL_KEY_FILE' does not exist." \
       "Put your service account key there, or run with" \
       "LOCAL_KEY_FILE=/path/to/key.json $0" >&2
  exit 1
fi
for _dir in "$API_DIR" "$WEB_DIR"; do
  if [ ! -f "$_dir/Dockerfile" ]; then
    echo "ERROR: no Dockerfile in '$_dir'." >&2
    exit 1
  fi
done
unset _dir

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

# Set explicitly rather than with --env-vars-file: gcloud expects that flag to
# point at a YAML file, and .env is KEY=value, which fails to parse.
COMMON_ENV="GCP_PROJECT_ID=${PROJECT_ID},GCP_BUCKET_NAME=${BUCKET_NAME},GCP_SERVICE_ACCOUNT_KEY=${SECRET_MOUNT_PATH}"

# ─── one-time project setup ───────────────────────────────────────────────────
bootstrap() {
  gcloud config set project "$PROJECT_ID"
  gcloud config set run/region "$REGION"
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com

  log "Storing the service account key in Secret Manager as '${GCP_KEY_SECRET}'"
  if ! gcloud secrets describe "$GCP_KEY_SECRET" >/dev/null 2>&1; then
    gcloud secrets create "$GCP_KEY_SECRET" --replication-policy=automatic
  fi
  gcloud secrets versions add "$GCP_KEY_SECRET" --data-file="$LOCAL_KEY_FILE"

  log "Letting the Cloud Run runtime service account read that secret"
  gcloud secrets add-iam-policy-binding "$GCP_KEY_SECRET" \
    --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
    --role=roles/secretmanager.secretAccessor

  log "Granting the runtime service account read/write on gs://${BUCKET_NAME}"
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
    --role=roles/storage.objectAdmin
}

# ─── API service ──────────────────────────────────────────────────────────────
deploy_api() {
  local build_dir
  build_dir="$(mktemp -d)"
  cp "$API_DIR/"*.py "$build_dir/"
  cp "$API_DIR/requirements.txt" "$API_DIR/Dockerfile" "$build_dir/"
  if [ -d "$API_DIR/collectors" ]; then
    cp -R "$API_DIR/collectors" "$build_dir/"
  fi
  # user_definition.py may live at the repo root rather than in api/
  if [ -f user_definition.py ] && [ ! -f "$build_dir/user_definition.py" ]; then
    cp user_definition.py "$build_dir/"
  fi

  log "Deploying ${API_SERVICE} from ${API_DIR} (Cloud Build builds the image)"
  gcloud run deploy "$API_SERVICE" \
    --source "$build_dir" \
    --region "$REGION" \
    --service-account="$RUNTIME_SERVICE_ACCOUNT" \
    --port="$API_PORT" \
    --allow-unauthenticated \
    --timeout="$RUN_TIMEOUT" \
    --memory="$RUN_MEMORY" \
    --max-instances=1 \
    --set-env-vars="$COMMON_ENV" \
    --set-secrets="$SECRET_MOUNT_PATH=$GCP_KEY_SECRET:latest"

  rm -rf "$build_dir"
}

api_url() {
  local url
  url=$(gcloud run services describe "$API_SERVICE" \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
  if [ -z "$url" ]; then
    echo "ERROR: could not resolve the URL for Cloud Run service" \
         "'$API_SERVICE' in $REGION. Deploy it first." >&2
    exit 1
  fi
  echo "$url"
}

# ─── Web app ──────────────────────────────────────────────────────────────────
deploy_web() {
  local url; url="$(api_url)"

  log "Deploying ${WEB_SERVICE} from ${WEB_DIR}, pointing at ${url}"
  gcloud run deploy "$WEB_SERVICE" \
    --source "$WEB_DIR" \
    --region "$REGION" \
    --service-account="$RUNTIME_SERVICE_ACCOUNT" \
    --port="$WEB_PORT" \
    --allow-unauthenticated \
    --memory="$RUN_MEMORY" \
    --max-instances=1 \
    --set-env-vars="${COMMON_ENV},API_SERVICE_URL=${url}" \
    --set-secrets="$SECRET_MOUNT_PATH=$GCP_KEY_SECRET:latest"
}

# ─── Cloud Scheduler ──────────────────────────────────────────────────────────
deploy_scheduler() {
  local url
  url="$(api_url)"

  local source action header_flag job_name job_path job_schedule

  for source in epa noaa festivals transform; do
    if [ "$source" = "transform" ]; then
      job_name="extract-and-save"
      job_path="$TRANSFORM_PATH"
      job_schedule="$TRANSFORM_SCHEDULE"
    else
      job_name="collect-${source}"
      job_path="/collect/raw_${source}"
      job_schedule="$SCHEDULE"
    fi

    action=create
    header_flag="--headers"

    if gcloud scheduler jobs describe "$job_name" \
      --location="$REGION" >/dev/null 2>&1; then
      action=update
      header_flag="--update-headers"
    fi

    log "${action}: ${job_name} -> ${url}${job_path} (${job_schedule})"
    gcloud scheduler jobs "$action" http "$job_name" \
      --location="$REGION" \
      --schedule="$job_schedule" \
      --time-zone="$SCHEDULER_TZ" \
      --uri="${url}${job_path}" \
      --http-method=POST \
      "${header_flag}=Content-Type=application/json" \
      --message-body="$MESSAGE_BODY" \
      --attempt-deadline="$SCHEDULER_DEADLINE"
  done
}

show_urls() {
  echo "API     : $(api_url)"
  echo "API docs: $(api_url)/docs"
  echo "Web app : $(gcloud run services describe "$WEB_SERVICE" \
    --region "$REGION" --format='value(status.url)')"
}

# ─── entry point ──────────────────────────────────────────────────────────────
case "${1:-all}" in
  all)       bootstrap; deploy_api; deploy_web; deploy_scheduler; show_urls ;;
  bootstrap) bootstrap ;;
  api)       deploy_api ;;
  web)       deploy_web ;;
  scheduler) deploy_scheduler ;;
  urls)      show_urls ;;
  *) echo "usage: $0 {all|bootstrap|api|web|scheduler|urls}" >&2; exit 1 ;;
esac

log "Done."