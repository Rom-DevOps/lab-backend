# lab-backend

FastAPI backend for the app — the API layer of the **k8s-lab-cloud** learning platform.

This repo holds **only the backend source** plus its CI. It builds a container image and
pushes it to Amazon ECR; the actual Kubernetes deployment is driven by GitOps from the
`lab-gitops` repo (ArgoCD).

## What it is

- A small DB-agnostic FastAPI service (SQLAlchemy ORM). Runs with `sqlite://` for quick
  local testing and `postgresql://` on the cluster.
- Configuration comes from environment variables (no hardcoding):
  - `DATABASE_URL` — DB connection string.
  - `WELCOME_MESSAGE` — text returned by the welcome endpoint.

### Endpoints

| Method | Path                  | Description            |
| ------ | --------------------- | ---------------------- |
| GET    | `/api/health`         | Health check.          |
| GET    | `/api/welcome`        | Returns welcome text.  |
| GET    | `/api/todos`          | List items.            |
| POST   | `/api/todos`          | Create an item.        |
| PUT    | `/api/todos/{id}`     | Update an item.        |
| DELETE | `/api/todos/{id}`     | Delete an item.        |

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8882 --reload
# defaults to sqlite:///./todo.db
```

The service listens on port **8882**.

## CI/CD

`.github/workflows/ci.yml` runs on push to `main` (doc-only changes ignored) and on manual
dispatch. It:

1. Authenticates to AWS via **OIDC** (assumes `${{ secrets.AWS_GHA_ROLE_ARN }}` — no static keys).
2. Logs in to **Amazon ECR**.
3. Builds the image with `--platform linux/amd64` (EKS nodes are amd64) from the repo root and
   pushes it to the ECR repo **`app-backend`** tagged with the commit SHA.

CI only builds and pushes; it does **not** deploy. Deployment is GitOps: bump
`image.backend.tag` in `lab-gitops` and ArgoCD syncs the cluster.

> **TODO (GitOps loop):** a follow-up CI step could auto-bump `image.backend.tag` in
> `lab-gitops` to the new SHA. That requires a cross-repo write token secret and is left as a
> documented TODO rather than an untested token flow.

- **Region:** `ap-south-1`

## Related repos

- Hub / monorepo reference: <https://github.com/Rom-DevOps/k8s-lab-cloud>
- Frontend: <https://github.com/Rom-DevOps/lab-frontend>
- GitOps (Helm/ArgoCD manifests): <https://github.com/Rom-DevOps/lab-gitops>
- Infrastructure (Terraform): <https://github.com/Rom-DevOps/lab-infra>
