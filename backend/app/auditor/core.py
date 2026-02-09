import subprocess
import json
import os

EXCLUDE_NS = os.getenv("EXCLUDE_NS", "kube-system,kube-public,local-path-storage,ingress-nginx,cert-manager").split(",")

def run_kubectl_get():
    """Fetches key resources in JSON format."""
    # Added horizontalpodautoscalers, ingresses, resourcequotas, poddisruptionbudgets, networkpolicies for new checks
    cmd = [
        "kubectl", "get", 
        "deployments,statefulsets,daemonsets,services,persistentvolumes,horizontalpodautoscalers,ingresses,resourcequotas,poddisruptionbudgets,networkpolicies", 
        "-A", "-o", "json"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"kubectl failed: {result.stderr}")
    return json.loads(result.stdout)
