# SRE Technical Assessment — Cloud Visibility Dashboard

## What the Application Does

A web application that provides infrastructure visibility through two endpoints on a single domain:

| Endpoint | Returns |
|----------|---------|
| `GET /k8s` | All Kubernetes Deployments across every namespace |
| `GET /s3` | All AWS S3 Buckets in the account |
| `GET /healthz` | Health check |

The scaffold is provided. Your job is to containerise it, configure the required authentication, write all Kubernetes manifests, and set up the CI/CD pipeline.

---

## How the Application Authenticates

The application uses **no hardcoded credentials anywhere**. It relies on two identity mechanisms that must be configured correctly before it works:

### 1. Kubernetes API — ServiceAccount (In-Cluster Auth)

When the pod runs inside the cluster, the application calls:

```python
k8s_config.load_incluster_config()
```

This automatically reads the ServiceAccount token mounted at `/var/run/secrets/kubernetes.io/serviceaccount/token` and uses it to authenticate against the Kubernetes API server.

**What you need to set up:**
- A dedicated `ServiceAccount` for the application
- A `ClusterRole` that grants `list` and `get` on `deployments` (across all namespaces)
- A `ClusterRoleBinding` that binds the ClusterRole to the ServiceAccount
- The `Deployment` must reference this ServiceAccount via `serviceAccountName`

Without this, the pod will get `403 Forbidden` when calling the Kubernetes API.

---

### 2. AWS S3 — IRSA (IAM Roles for Service Accounts)

When the application calls:

```python
boto3.client("s3")
```

The AWS SDK automatically looks for two environment variables that **EKS injects into the pod** when IRSA is configured:

```
AWS_ROLE_ARN=arn:aws:iam::<account-id>:role/<role-name>
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

The SDK exchanges the pod's ServiceAccount OIDC token for temporary AWS credentials via STS — **no access keys, no secrets**.

**Required IAM permissions for the role:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation"
      ],
      "Resource": "*"
    }
  ]
}
```

How the IAM role is created, how it trusts the cluster, and how the pod assumes it — that is for you to figure out.

---

## Requirements

### Kubernetes Manifests

Write all manifests from scratch:

- `ServiceAccount` — with the IRSA annotation
- `ClusterRole` — least privilege, only what the app needs
- `ClusterRoleBinding` — binds the ClusterRole to the ServiceAccount
- `Deployment` — references the ServiceAccount, sets probes and resource limits
- `Service` — exposes the application inside the cluster
- `Ingress` — routes external traffic to the service

### CI/CD Pipeline

- Every push to `main` triggers the pipeline
- Pipeline builds the Docker image, pushes to a registry, deploys to Kubernetes, and verifies the rollout
- Image tags must be traceable to a Git commit
- No static AWS credentials in pipeline secrets — use OIDC federation

### Security

- Least privilege on all RBAC and IAM — nothing more than what the app needs
- No credentials hardcoded anywhere in code, manifests, or the pipeline

---

## Deliverables

```
├── Dockerfile
├── k8s/
│   ├── serviceaccount.yaml
│   ├── clusterrole.yaml
│   ├── clusterrolebinding.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── .github/workflows/
│   └── deploy.yml
└── README.md              ← your own setup and verification instructions
```

---

## Submission

1. Fork this repository
2. Work on a branch named `solution/<your-name>`
3. Open a Pull Request to `main` on your fork with:
   - Screenshots of `/k8s` and `/s3` returning data
   - A short explanation of your design decisions

**Deadline:** To be communicated by your manager.

---

## Questions?

Open a GitHub Issue and tag it `question`.
