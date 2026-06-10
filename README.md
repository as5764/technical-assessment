# SRE Technical Assessment — Cloud Visibility Dashboard

## Objective

Build and deploy a **Cloud Visibility Dashboard** — a web application that provides infrastructure visibility through two endpoints on a single domain:

| Endpoint | What it returns |
|----------|----------------|
| `GET /k8s` | All Kubernetes Deployments across every namespace |
| `GET /s3` | All AWS S3 Buckets in the account |
| `GET /healthz` | Health check |

The application runs on Kubernetes, authenticates to both the Kubernetes API and AWS without any hardcoded credentials, and is deployed automatically via a CI/CD pipeline.

---

## Requirements

### Application

- The scaffold is provided in `app/` — you may extend it or rewrite it in any language
- Copy `app/.env.example` to `app/.env` for local development
- The app must work both locally (using `~/.kube/config` and an AWS profile) and inside the cluster (using a ServiceAccount and an IAM role)

### Kubernetes

- Run as a `Deployment` with at least 2 replicas
- Expose via a `Service` and an `Ingress` on a domain of your choice
- The app needs cluster-wide read access to Deployments — set up the right Kubernetes access model
- Set liveness and readiness probes
- Set resource requests and limits

### AWS

- List all S3 Buckets in the account
- The pod must authenticate to AWS without any access keys in the code or manifests
- Research how EKS enables pods to assume an IAM role natively

### CI/CD

- Every push to `main` must trigger the pipeline automatically
- Pipeline must: build the image → push to a registry → deploy to Kubernetes → verify rollout
- Image tags must be traceable to a Git commit

### Security

- Least privilege everywhere — Kubernetes RBAC, IAM policy, and pipeline credentials
- No hardcoded secrets or credentials anywhere

---

## Concepts You Will Need

- Kubernetes ServiceAccounts and RBAC (ClusterRole, ClusterRoleBinding)
- In-cluster Kubernetes API authentication
- IRSA — IAM Roles for Service Accounts
- Kubernetes Ingress
- GitHub Actions for CI/CD
- Docker image build and push

---

## Deliverables

Your fork must contain:

```
├── app/                    # Application source code + Dockerfile
├── k8s/                    # All Kubernetes manifests
│   └── rbac/               # ServiceAccount, ClusterRole, ClusterRoleBinding
├── .github/workflows/      # CI/CD pipeline
└── README.md               # Your own setup and verification instructions
```

Your `README.md` must cover:
- How to deploy from scratch
- What needs to be set up in AWS and Kubernetes beforehand
- How to verify both endpoints work

---

## Submission

1. Fork this repository
2. Work on a branch named `solution/<your-name>`
3. Open a Pull Request to `main` on your fork with:
   - Screenshots of both `/k8s` and `/s3` returning data
   - A short explanation of your design decisions

**Deadline:** To be communicated by your manager.

---

## Questions?

Open a GitHub Issue and tag it `question`.
