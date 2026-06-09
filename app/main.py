"""
Cloud Visibility Dashboard — starter scaffold (Python / Flask).
Candidates may rewrite this in any language.
"""
import os
import json
from flask import Flask, jsonify, request, render_template_string, abort

# kubernetes and boto3 are imported lazily so the scaffold runs without them installed
try:
    from kubernetes import client as k8s_client, config as k8s_config
    _K8S_AVAILABLE = True
except ImportError:
    _K8S_AVAILABLE = False

try:
    import boto3
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False

app = Flask(__name__)

DOMAIN_ENV_MAP = {
    "prod": "production",
    "staging": "staging",
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Cloud Visibility Dashboard — {{ env }}</title>
<style>
  body { font-family: sans-serif; margin: 2rem; }
  h1 { color: #333; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
  th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
  th { background: #f4f4f4; }
  .env-badge { background: {{ '#2e7d32' if env == 'production' else '#1565c0' }};
               color: white; padding: 2px 10px; border-radius: 4px; font-size: 0.85rem; }
</style>
</head>
<body>
<h1>Cloud Visibility Dashboard <span class="env-badge">{{ env }}</span></h1>

<h2>Kubernetes Deployments</h2>
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

<h2>S3 Buckets (tagged env={{ env }})</h2>
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


def resolve_environment(host: str) -> str:
    """Derive the target environment from the HTTP Host header."""
    host_lower = host.split(":")[0].lower()  # strip port
    for fragment, env in DOMAIN_ENV_MAP.items():
        if host_lower.startswith(f"dashboard-{fragment}"):
            return env
    # Allow local override for development
    override = os.environ.get("HOST_OVERRIDE", "")
    for fragment, env in DOMAIN_ENV_MAP.items():
        if override.startswith(f"dashboard-{fragment}"):
            return env
    abort(400, description=f"Unknown host: {host}. Expected dashboard-prod.* or dashboard-staging.*")


def list_deployments(env: str) -> list:
    if not _K8S_AVAILABLE:
        return [{"namespace": "mock-ns", "name": "mock-deploy", "desired": 2, "ready": 2, "image": "nginx:latest"}]

    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    v1 = k8s_client.CoreV1Api()
    apps_v1 = k8s_client.AppsV1Api()

    namespaces = [ns.metadata.name for ns in v1.list_namespace().items if env in ns.metadata.name]

    results = []
    for ns in namespaces:
        for d in apps_v1.list_namespaced_deployment(ns).items:
            image = d.spec.template.spec.containers[0].image if d.spec.template.spec.containers else "unknown"
            results.append({
                "namespace": ns,
                "name": d.metadata.name,
                "desired": d.spec.replicas or 0,
                "ready": (d.status.ready_replicas or 0),
                "image": image,
            })
    return results


def list_s3_buckets(env: str) -> list:
    if not _BOTO3_AVAILABLE:
        return [{"name": "mock-bucket", "region": "ap-south-1", "created": "2024-01-01"}]

    s3 = boto3.client("s3")
    all_buckets = s3.list_buckets().get("Buckets", [])

    results = []
    for bucket in all_buckets:
        name = bucket["Name"]
        try:
            tags = s3.get_bucket_tagging(Bucket=name).get("TagSet", [])
            env_tag = next((t["Value"] for t in tags if t["Key"] == "env"), None)
            if env_tag != env:
                continue
        except s3.exceptions.ClientError:
            continue

        try:
            region = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
        except Exception:
            region = "unknown"

        results.append({
            "name": name,
            "region": region,
            "created": str(bucket.get("CreationDate", ""))[:10],
        })
    return results


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.get("/api/deployments")
def api_deployments():
    env = resolve_environment(request.host)
    return jsonify(list_deployments(env))


@app.get("/api/buckets")
def api_buckets():
    env = resolve_environment(request.host)
    return jsonify(list_s3_buckets(env))


@app.get("/")
def index():
    env = resolve_environment(request.host)
    return render_template_string(
        DASHBOARD_HTML,
        env=env,
        deployments=list_deployments(env),
        buckets=list_s3_buckets(env),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
