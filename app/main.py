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
    from botocore.exceptions import ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False
    ClientError = Exception  # fallback so the name is always defined

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Cloud Visibility Dashboard — {{ scope }}</title>
<style>
  body { font-family: sans-serif; margin: 2rem; }
  h1 { color: #333; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
  th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
  th { background: #f4f4f4; }
  .scope-badge { background: #37474f; color: white; padding: 2px 10px;
                 border-radius: 4px; font-size: 0.85rem; }
</style>
</head>
<body>
<h1>Cloud Visibility Dashboard <span class="scope-badge">{{ scope }}</span></h1>

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

<h2>S3 Buckets</h2>
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


def resolve_scope(host: str) -> str:
    """
    Extract the scope from the HTTP Host header.
    The first subdomain label is used as-is as the scope.
    e.g.  team-a.example.com  →  scope = "team-a"
          infra.example.com   →  scope = "infra"
    A HOST_OVERRIDE env var can be set for local development.
    """
    override = os.environ.get("HOST_OVERRIDE", "")
    effective_host = override if override else host
    label = effective_host.split(":")[0].split(".")[0].lower()  # first label, strip port
    if not label:
        abort(400, description="Cannot resolve scope: Host header is empty or invalid.")
    return label


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
    all_buckets = s3.list_buckets().get("Buckets", [])

    results = []
    for bucket in all_buckets:
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


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.get("/api/deployments")
def api_deployments():
    return jsonify(list_deployments())


@app.get("/api/buckets")
def api_buckets():
    return jsonify(list_s3_buckets())


@app.get("/")
def index():
    scope = resolve_scope(request.host)
    return render_template_string(
        DASHBOARD_HTML,
        scope=scope,
        deployments=list_deployments(),
        buckets=list_s3_buckets(),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
