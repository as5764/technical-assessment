# Technical Assessment — Cloud Visibility Dashboard

## Overview

Build and deploy a **Cloud Visibility Dashboard** — a web application that lists:
1. All Kubernetes **Deployments** across every namespace in a cluster
2. All **AWS S3 buckets**, grouped by the environment tag that matches the namespace name

The same application must be deployed once but serve **two different outputs** based on the domain used to access it.

The app extracts the **first subdomain label** from the HTTP `Host` header and uses it as the scope — no hardcoded environment names.

| Domain | Resolved Scope | Output |
|--------|---------------|--------|
| `team-a.<your-domain>` | `team-a` | Namespaces containing `team-a` + S3 buckets tagged `env=team-a` |
| `infra.<your-domain>` | `infra` | Namespaces containing `infra` + S3 buckets tagged `env=infra` |
| `<anything>.<your-domain>` | `<anything>` | Namespaces + buckets matching that label |

The scope value is used as-is — the candidate defines the two domain names they deploy with.

---

## Architecture

```
GitHub Push
    │
    ▼
GitHub Actions CI/CD
    │  ┌─────────────────────────────────────────┐
    │  │  1. Build Docker image                  │
    │  │  2. Push to container registry (ECR)    │
    │  │  3. kubectl rollout (or Helm upgrade)   │
    │  └─────────────────────────────────────────┘
    │
    ▼
Kubernetes Cluster
    │
    ├── Ingress (2 hosts → 1 Service)
    │     ├── <scope-a>.<domain>  ──┐
    │     └── <scope-b>.<domain>  ──┤
    │                                     ▼
    ├── Service → Pod (single Deployment)
    │     └── App reads Host header → scopes query
    │
    ├── ServiceAccount + ClusterRoleBinding
    │     └── Permissions: list Deployments & Namespaces
    │
    └── Pod IAM Role (IRSA / kube2iam)
          └── Permissions: s3:ListAllMyBuckets, s3:GetBucketTagging
```

---

## Application Requirements

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | HTML dashboard — K8s deployments + S3 buckets for the resolved environment |
| `GET /api/deployments` | JSON list of deployments for the resolved environment |
| `GET /api/buckets` | JSON list of S3 buckets for the resolved environment |
| `GET /healthz` | Health check — returns `{ "status": "ok" }` |

### Scope Resolution Logic

The first subdomain label of the `Host` header is the scope — no mapping, no hardcoding.

```
Host: team-a.example.com   → scope = "team-a"
Host: infra.example.com    → scope = "infra"
Host: payments.example.com → scope = "payments"
```

The candidate chooses the two domain names they deploy with. Whatever they pick, the app must return different data for each.

### K8s Deployment Filtering

- List all namespaces; filter those where the namespace **name contains** the resolved scope string
  (e.g., scope `team-a` matches namespaces: `team-a`, `team-a-jobs`, `team-a-infra`)
- Return: namespace, deployment name, desired replicas, ready replicas, image tags, age

### S3 Bucket Filtering

- List all S3 buckets; for each bucket, call `GetBucketTagging`
- Return only buckets where tag `env` equals the resolved scope string
- Return: bucket name, region, creation date, size (optional — bonus)

---

## Tech Stack (You Choose)

The language and framework are your choice. Recommended options:

- **Python** — Flask/FastAPI + `kubernetes` client + `boto3`
- **Go** — `gin`/`chi` + `client-go` + `aws-sdk-go-v2`
- **Node.js** — Express + `@kubernetes/client-node` + `@aws-sdk/client-s3`

The only hard requirements are:
- Runs as a Docker container
- Reads Kubernetes API in-cluster (uses mounted ServiceAccount token)
- Reads AWS using IAM role attached to the pod (no hardcoded credentials)
- Responds differently based on the `Host` header

---

## Deliverables

```
technical-assessment/
├── app/
│   ├── Dockerfile
│   ├── main.<ext>          # application entry point
│   └── requirements.txt    # (or go.mod / package.json)
├── k8s/
│   ├── rbac/
│   │   ├── serviceaccount.yaml
│   │   ├── clusterrole.yaml
│   │   └── clusterrolebinding.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── .github/
│   └── workflows/
│       └── deploy.yml
└── README.md
```

All Kubernetes manifests must be parameterized via environment variables or Helm values (no hardcoded cluster names, image tags, or domain names).

---

## Required Permissions

### 1. Kubernetes RBAC

The application runs under a dedicated `ServiceAccount`. Apply the following:

```yaml
# k8s/rbac/clusterrole.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: dashboard-viewer
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
```

```yaml
# k8s/rbac/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dashboard-sa
  namespace: dashboard
  # If using IRSA (EKS), add the annotation below:
  # annotations:
  #   eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/dashboard-role
```

```yaml
# k8s/rbac/clusterrolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dashboard-viewer-binding
subjects:
  - kind: ServiceAccount
    name: dashboard-sa
    namespace: dashboard
roleRef:
  kind: ClusterRole
  name: dashboard-viewer
  apiGroup: rbac.authorization.k8s.io
```

### 2. AWS IAM Policy

Create and attach the following policy to the IAM role used by the pod (via IRSA on EKS, or kube2iam/kiam on self-managed):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBuckets",
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadBucketTags",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketTagging"
      ],
      "Resource": "arn:aws:s3:::*"
    }
  ]
}
```

> **Note:** No `s3:GetObject` or `s3:PutObject` is needed. The app only introspects bucket metadata.

### 3. GitHub Actions Secrets

Set the following secrets in your fork of this repo (`Settings → Secrets and variables → Actions`):

| Secret Name | Description |
|-------------|-------------|
| `AWS_ROLE_ARN` | ARN of the IAM role for OIDC federation (preferred) |
| `AWS_REGION` | AWS region, e.g. `ap-south-1` |
| `KUBE_CONFIG` | Base64-encoded kubeconfig with deploy permissions |
| `REGISTRY` | Container registry URL (ECR, Docker Hub, GHCR) |
| `IMAGE_NAME` | Image name, e.g. `dashboard` |

> **Preferred:** Use GitHub OIDC (`aws-actions/configure-aws-credentials@v4` with `role-to-assume`) instead of static `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`. This avoids long-lived credentials in secrets.

---

## CI/CD Pipeline Requirements

The pipeline in `.github/workflows/deploy.yml` must:

1. **Trigger** on every push to `main`
2. **Build** the Docker image and tag it with the Git SHA (`ghcr.io/<org>/<image>:<sha>`)
3. **Push** the image to a container registry
4. **Deploy** to Kubernetes by updating the deployment image tag  
   (use `kubectl set image` or `helm upgrade --install`)
5. **Verify** the rollout succeeds (`kubectl rollout status`)

---

## Kubernetes Ingress

Deploy a single `Deployment` + `Service`, but create two `Ingress` rules pointing at the same service:

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-ingress
  namespace: dashboard
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    - host: <SCOPE_A>.<YOUR_DOMAIN>       # e.g. team-a.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dashboard-svc
                port:
                  number: 80
    - host: <SCOPE_B>.<YOUR_DOMAIN>       # e.g. infra.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dashboard-svc
                port:
                  number: 80
```

---

## Evaluation Criteria

| Area | Weight | What we look for |
|------|--------|-----------------|
| **Correctness** | 30% | App returns accurate data; domain routing works |
| **Security** | 25% | Least-privilege RBAC & IAM; no hardcoded credentials; OIDC over static keys |
| **CI/CD** | 20% | Pipeline triggers, builds, and deploys cleanly on push |
| **Code quality** | 15% | Clean structure, error handling, readable code |
| **Documentation** | 10% | Clear setup instructions, env vars documented |

### Bonus points
- TLS on both Ingress rules (cert-manager / Let's Encrypt)
- Helm chart instead of raw manifests
- Unit tests for the host-resolution logic
- `/metrics` endpoint (Prometheus format) exposing request counts per domain

---

## Submission

1. Fork this repository
2. Implement the solution on a branch named `solution/<your-name>`
3. Open a Pull Request back to `main` with:
   - A short description of your design choices
   - Screenshots of both domains returning different data
   - Any assumptions you made

**Deadline:** To be communicated by your manager.

---

## Getting Started Locally

```bash
# Run against a local kubeconfig + AWS profile
export KUBECONFIG=~/.kube/config
export AWS_PROFILE=your-profile
export HOST_OVERRIDE=team-a.localhost   # simulate any scope — change to test different outputs

# Python example
pip install -r app/requirements.txt
python app/main.py

# Visit http://localhost:8080
# Change HOST_OVERRIDE to a different value to simulate the second domain
```

---

## Questions?

Open a GitHub Issue on this repository. Tag it `question`.
