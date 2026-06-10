"""
Cloud Visibility Dashboard — starter scaffold (Python / Flask).
Candidates may rewrite this in any language.

Domain A  →  Kubernetes Deployments viewer
Domain B  →  AWS S3 Buckets viewer

The app reads the Host header to decide which functionality to serve.
The two domain names are configured in the Ingress and as env vars (DOMAIN_K8S, DOMAIN_S3).
"""
import os
from flask import Flask, jsonify, request, render_template_string, abort

try:
    from kubernetes import client as k8s_client, config as k8s_config
    _K8S_AVAILABLE = True
except ImportError:
    _K8S_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False
    ClientError = Exception

app = Flask(__name__)

# Configured via environment variables — set these in your Deployment manifest
DOMAIN_K8S = os.environ.get("DOMAIN_K8S", "")  # e.g. k8s.example.com
DOMAIN_S3  = os.environ.get("DOMAIN_S3", "")   # e.g. s3.example.com

DEPLOYMENTS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Kubernetes Deployments</title>
<style>
  body { font-family: sans-serif; margin: 2rem; }
  h1 { color: #1a237e; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
  th { background: #e8eaf6; }
</style>
</head>
<body>
<h1>Kubernetes Deployments</h1>
<table>
  <tr><th>Namespace</th><th>Deployment</th><th>Desired</th><th>Ready</th><th>Image</th></tr>
  {% for d in deployments %}
  <tr>
    <td>{{ d.namespace }}</td>
    <td>{{ d.name }}</td>
    <td>{{ d.desired }}</td>
    <td>{{ d.ready }}</td>
    <td><code>{{ d.image }}</code></td>
  </tr>
  {% else %}
  <tr><td colspan="5">No deployments found</td></tr>
  {% endfor %}
</table>
</body>
</html>
"""

BUCKETS_HTML = """
<!DOCTYPE html>
<html>
<head><title>S3 Buckets</title>
<style>
  body { font-family: sans-serif; margin: 2rem; }
  h1 { color: #1b5e20; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
  th { background: #e8f5e9; }
</style>
</head>
<body>
<h1>AWS S3 Buckets</h1>
<table>
  <tr><th>Bucket</th><th>Region</th><th>Created</th></tr>
  {% for b in buckets %}
  <tr>
    <td>{{ b.name }}</td>
    <td>{{ b.region }}</td>
    <td>{{ b.created }}</td>
  </tr>
  {% else %}
  <tr><td colspan="3">No buckets found</td></tr>
  {% endfor %}
</table>
</body>
</html>
"""


def resolve_domain(host: str) -> str:
    """
    Returns 'k8s' or 's3' based on which configured domain matches the Host header.
    Falls back to DOMAIN_OVERRIDE env var for local testing.
    """
    override = os.environ.get("DOMAIN_OVERRIDE", "")
    effective = override if override else host.split(":")[0].lower()

    if DOMAIN_K8S and effective == DOMAIN_K8S:
        return "k8s"
    if DOMAIN_S3 and effective == DOMAIN_S3:
        return "s3"

    # When env vars are not set (local dev), derive from the first subdomain label
    label = effective.split(".")[0]
    if label in ("k8s", "kubernetes"):
        return "k8s"
    if label in ("s3", "storage", "aws"):
        return "s3"

    abort(400, description=f"Unrecognised host '{effective}'. Set DOMAIN_K8S and DOMAIN_S3 env vars.")


def list_deployments() -> list:
    if not _K8S_AVAILABLE:
        return [{"namespace": "mock-ns", "name": "mock-deploy", "desired": 2, "ready": 2, "image": "nginx:latest"}]

    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    apps_v1 = k8s_client.AppsV1Api()
    results = []
    for d in apps_v1.list_deployment_for_all_namespaces().items:
        image = d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else "unknown"
        results.append({
            "namespace": d.metadata.namespace,
            "name": d.metadata.name,
            "desired": d.spec.replicas or 0,
            "ready": d.status.ready_replicas or 0,
            "image": image,
        })
    return results


def list_s3_buckets() -> list:
    if not _BOTO3_AVAILABLE:
        return [{"name": "mock-bucket", "region": "ap-south-1", "created": "2024-01-01"}]

    s3 = boto3.client("s3")
    results = []
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            region = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
        except ClientError:
            region = "unknown"
        results.append({
            "name": name,
            "region": region,
            "created": str(bucket.get("CreationDate", ""))[:10],
        })
    return results


# ── Health check ────────────────────────────────────────────────────────────

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# ── Domain A — Kubernetes Deployments ───────────────────────────────────────

@app.get("/deployments")
def api_deployments():
    if resolve_domain(request.host) != "k8s":
        abort(404)
    return jsonify(list_deployments())


# ── Domain B — S3 Buckets ────────────────────────────────────────────────────

@app.get("/buckets")
def api_buckets():
    if resolve_domain(request.host) != "s3":
        abort(404)
    return jsonify(list_s3_buckets())


# ── Root — renders the right dashboard based on domain ──────────────────────

@app.get("/")
def index():
    domain = resolve_domain(request.host)
    if domain == "k8s":
        return render_template_string(DEPLOYMENTS_HTML, deployments=list_deployments())
    if domain == "s3":
        return render_template_string(BUCKETS_HTML, buckets=list_s3_buckets())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
