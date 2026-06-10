# SRE Technical Assessment — Cloud Visibility Dashboard

## Objective

Build and deploy a **Cloud Visibility Dashboard** — a web application that gives visibility into your infrastructure by listing:

1. All Kubernetes **Deployments** across namespaces
2. All **AWS S3 Buckets** relevant to those namespaces

The application must be deployed on Kubernetes, built and deployed automatically via a CI/CD pipeline, and must serve **different outputs depending on the domain used to access it** — using a single deployment.

---

## Requirements

### Application

- Expose the following HTTP endpoints:

  | Endpoint | Description |
  |----------|-------------|
  | `GET /` | HTML page showing deployments and S3 buckets |
  | `GET /api/deployments` | JSON list of Kubernetes deployments |
  | `GET /api/buckets` | JSON list of S3 buckets |
  | `GET /healthz` | Health check |

- The app must determine its **scope** from the incoming HTTP request — no environment variables, no config files, no hardcoding
- Based on the scope, filter and return only the relevant namespaces and S3 buckets
- The app must run inside the cluster and talk to the Kubernetes API and AWS — think carefully about how it authenticates to each

### Kubernetes

- The app must run as a Kubernetes `Deployment` with at least 2 replicas
- It must be accessible via two different domain names, both pointing to the same service — the response must differ based on which domain was used
- The app must be able to list deployments and namespaces cluster-wide — figure out the right Kubernetes access model to enable this securely
- Define liveness and readiness probes
- Set resource requests and limits

### AWS

- The app must list S3 buckets and filter them by a tag that corresponds to the resolved scope
- The app must authenticate to AWS without any hardcoded credentials or access keys anywhere in the code or manifests
- Think about how pods on your cluster can securely assume an AWS identity

### CI/CD

- Every push to `main` must automatically build the Docker image, push it to a container registry, and deploy the updated image to Kubernetes
- The pipeline must verify the deployment rolled out successfully before marking the run as passed
- Image tags must be traceable back to a specific Git commit

### Security

- Apply the **principle of least privilege** everywhere — Kubernetes access, AWS access, and pipeline credentials
- No secrets, tokens, or credentials hardcoded anywhere

---

## Concepts You Will Need

You are expected to research and apply the following — no implementation details are provided intentionally:

- Kubernetes ServiceAccounts and RBAC
- In-cluster Kubernetes API authentication
- AWS IAM roles for pods (look up how EKS enables this natively)
- S3 bucket tagging and filtering
- Kubernetes Ingress and host-based routing
- GitHub Actions (or equivalent) for CI/CD
- Docker image build and push

---

## Deliverables

Your fork must contain:

```
├── app/                    # Application source code + Dockerfile
├── k8s/                    # All Kubernetes manifests
│   └── rbac/               # ServiceAccount, Role/ClusterRole, Binding
├── .github/workflows/      # CI/CD pipeline
└── README.md               # Setup and verification instructions (your own)
```

Write your own `README.md` explaining:
- How to deploy the application from scratch
- What pre-requisites are needed (cluster, AWS setup, secrets)
- How to verify both domains return different data

---

## Submission

1. Fork this repository
2. Work on a branch named `solution/<your-name>`
3. Open a Pull Request to `main` on your fork with:
   - Screenshots of both domains returning different outputs
   - A brief explanation of your design decisions

**Deadline:** To be communicated by your manager.

---

## Questions?

Open a GitHub Issue and tag it `question`.
