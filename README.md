# SRE Technical Assessment — Cloud Visibility Dashboard

## Objective

Build and deploy a **Cloud Visibility Dashboard** — a web application that provides infrastructure visibility across two concerns:

- One domain shows all **Kubernetes Deployments** across every namespace
- Another domain shows all **AWS S3 Buckets** in the account

Both domains must be served by a **single deployment** on Kubernetes. The application decides what to show based on which domain the request came in on.

---

## Requirements

### Application

Expose the following endpoints:

| Endpoint | Domain | Description |
|----------|--------|-------------|
| `GET /` | Both | HTML dashboard relevant to the domain |
| `GET /deployments` | K8s domain only | JSON — all deployments across all namespaces |
| `GET /buckets` | S3 domain only | JSON — all S3 buckets |
| `GET /healthz` | Both | Health check |

- The app must read the incoming `Host` header to decide what to serve
- Hitting the wrong endpoint for the wrong domain should return a `404`
- The app authenticates to Kubernetes and AWS — figure out how to do this securely without hardcoding any credentials

### Kubernetes

- Run as a `Deployment` with at least 2 replicas
- Two different domain names must point to the same service — the app handles the routing logic internally
- The app needs cluster-wide read access to deployments — use the right Kubernetes access model
- Set liveness and readiness probes
- Set resource requests and limits

### AWS

- List all S3 buckets in the account
- Authenticate to AWS using the pod's identity — no access keys in code or manifests
- Think about how EKS enables pods to assume an IAM role natively

### CI/CD

- Every push to `main` triggers the pipeline automatically
- Pipeline must: build the image → push to a registry → deploy to Kubernetes → verify rollout
- Image tags must be traceable to a Git commit

### Security

- Least privilege everywhere — Kubernetes RBAC, IAM, and pipeline credentials
- No hardcoded secrets or credentials anywhere

---

## Concepts You Will Need

No implementation details are given — you are expected to research and apply:

- Kubernetes ServiceAccounts and RBAC (ClusterRole, ClusterRoleBinding)
- In-cluster Kubernetes API authentication
- IRSA — IAM Roles for Service Accounts (EKS-native way to give pods AWS access)
- Kubernetes Ingress with host-based routing
- GitHub Actions for CI/CD
- Docker image build and push to a registry

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

Your `README.md` must explain:
- How to deploy from scratch
- What needs to be set up in AWS and Kubernetes before deploying
- How to verify both domains work and return different data

---

## Submission

1. Fork this repository
2. Work on a branch named `solution/<your-name>`
3. Open a Pull Request to `main` on your fork with:
   - Screenshots of both domains returning different outputs
   - A short explanation of your design decisions

**Deadline:** To be communicated by your manager.

---

## Questions?

Open a GitHub Issue and tag it `question`.
