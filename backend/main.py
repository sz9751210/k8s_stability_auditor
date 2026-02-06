from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os
import datetime

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCLUDE_NS = os.getenv("EXCLUDE_NS", "kube-system,kube-public,local-path-storage,ingress-nginx,cert-manager").split(",")

def run_kubectl_get():
    """Fetches key resources in JSON format."""
    # Added services, persistentvolumes for FinOps
    cmd = ["kubectl", "get", "deployments,statefulsets,daemonsets,services,persistentvolumes", "-A", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"kubectl failed: {result.stderr}")
    return json.loads(result.stdout)

def check_resources(container, kind, name, ns, issues):
    """Checks for resource requests/limits and QoS."""
    resources = container.get("resources", {})
    requests = resources.get("requests", {})
    limits = resources.get("limits", {})
    
    if not requests:
        issues.append({
            "Issue_Level": "CRITICAL",
            "Issue_Type": "Missing Requests",
            "Category": "Stability",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Define resources.requests"
        })
    if not limits:
        issues.append({
            "Issue_Level": "CRITICAL",
            "Issue_Type": "Missing Limits",
            "Category": "Stability",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Define resources.limits"
        })
    
    # FinOps: Check if Requests are Huge (Goliath Pods)
    # Simple heuristic: > 4 CPU or > 16Gi Memory
    req_cpu = requests.get("cpu", "0")
    req_mem = requests.get("memory", "0")
    
    # Very naive parse for demo (handles '4', '4000m', '16Gi', '16000Mi')
    # Real production should use a unit parser library.
    # We'll just flag clear integers > 4 for CPU.
    if req_cpu.isdigit() and int(req_cpu) >= 4:
         issues.append({
            "Issue_Level": "WARN",
            "Issue_Type": "High Resource Request",
            "Category": "FinOps",
            "Detail": f"Container: {container['name']} requests {req_cpu} CPU",
            "Recommendation": "Review if this large allocation is efficiently used"
        })


def check_probes(container, kind, name, ns, issues):
    """Checks for Liveness and Readiness probes."""
    if "livenessProbe" not in container:
        issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Missing LivenessProbe",
            "Category": "Stability",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Add livenessProbe"
        })
    if "readinessProbe" not in container:
        issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Missing ReadinessProbe",
            "Category": "Stability",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Add readinessProbe"
        })

def check_image_tag(container, kind, name, ns, issues):
    """Checks if image uses latest tag or no tag."""
    image = container.get("image", "")
    if image.endswith(":latest") or ":" not in image:
        issues.append({
            "Issue_Level": "WARN",
            "Issue_Type": "Using Latest Tag",
            "Category": "Stability",
            "Detail": f"Container: {container['name']} ({image})",
            "Recommendation": "Use specific version tag"
        })

def check_security(container, kind, name, ns, issues):
    """Checks for privileged, root, and capabilities."""
    security_context = container.get("securityContext", {})
    
    # Privileged
    if security_context.get("privileged") is True:
        issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Privileged Container",
            "Category": "Security",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Avoid privileged mode"
        })
        
    # RunAsRoot
    if security_context.get("runAsUser") == 0:
         issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Runs as Root",
            "Category": "Security",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Set runAsUser to non-zero"
        })
    
    # Dangerous Capabilities
    caps = security_context.get("capabilities", {}).get("add", [])
    dangerous = ["SYS_ADMIN", "NET_ADMIN", "ALL"]
    for d in dangerous:
        if d in caps:
            issues.append({
                "Issue_Level": "HIGH",
                "Issue_Type": f"Example Dangerous Capability: {d}",
                "Category": "Security",
                "Detail": f"Container: {container['name']} adds {d}",
                "Recommendation": f"Drop {d} capability"
            })

def check_pod_security(spec, kind, name, ns, results, timestamp):
    """Pod-level security context (hostNetwork, etc)"""
    if spec.get("hostNetwork") is True:
        results.append({
            "Timestamp": timestamp,
            "Namespace": ns,
            "Type": kind,
            "Name": name,
            "Issue_Level": "HIGH",
            "Issue_Type": "Host Network Access",
            "Category": "Security",
            "Detail": "hostNetwork: true",
            "Recommendation": "Disable hostNetwork to isolate network"
        })
    if spec.get("hostPID") is True:
         results.append({
            "Timestamp": timestamp,
            "Namespace": ns,
            "Type": kind,
            "Name": name,
            "Issue_Level": "HIGH",
            "Issue_Type": "Host PID Access",
            "Category": "Security",
            "Detail": "hostPID: true",
            "Recommendation": "Disable hostPID"
        })

def audit_pvs(items, results, timestamp):
    """Check for Released PVs."""
    for item in items:
        if item.get("kind") == "PersistentVolume":
            status = item.get("status", {}).get("phase")
            name = item.get("metadata", {}).get("name")
            if status == "Released":
                results.append({
                    "Timestamp": timestamp,
                    "Namespace": "cluster-scope",
                    "Type": "PersistentVolume",
                    "Name": name,
                    "Issue_Level": "WARN",
                    "Issue_Type": "Unused PV Cost",
                    "Category": "FinOps",
                    "Detail": "Status is Released (Retain policy?)",
                    "Recommendation": "Delete or Reclaim Volume"
                })

def audit_services(items, results, timestamp):
    """Check for Unused LoadBalancers."""
    for item in items:
        if item.get("kind") == "Service":
            spec = item.get("spec", {})
            meta = item.get("metadata", {})
            name = meta.get("name")
            ns = meta.get("namespace")
            
            if ns in EXCLUDE_NS: continue

            if spec.get("type") == "LoadBalancer":
                # Check if it has selector. If no selector, manual EP. 
                # If selector exists, but we can't check pods easily in this simple loop without mapping.
                # Heuristic: Check if LoadBalancer IP is assigned.
                ingress = item.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                if not ingress:
                     results.append({
                        "Timestamp": timestamp,
                        "Namespace": ns,
                        "Type": "Service",
                        "Name": name,
                        "Issue_Level": "WARN",
                        "Issue_Type": "Unprovisioned LB",
                        "Category": "FinOps",
                        "Detail": "LoadBalancer ingress empty",
                        "Recommendation": "Check cloud provider status"
                    })
                # If we had endpoint data, checking for 0 endpoints would be better for FinOps (Paying for LB with no backends)

def audit_workloads(data):
    results = []
    items = data.get("items", [])
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    audit_pvs(items, results, timestamp)
    audit_services(items, results, timestamp)

    for item in items:
        metadata = item.get("metadata", {})
        ns = metadata.get("namespace", "default")
        name = metadata.get("name", "unknown")
        kind = item.get("kind", "unknown")
        
        # Skip PV/Service here as handled above
        if kind in ["PersistentVolume", "Service"]: continue

        if ns in EXCLUDE_NS:
            continue

        spec = item.get("spec", {})
        
        # Replica Check (Deployment only)
        if kind == "Deployment":
            replicas = spec.get("replicas", 1)
            if replicas == 1:
                results.append({
                    "Timestamp": timestamp,
                    "Namespace": ns,
                    "Type": kind,
                    "Name": name,
                    "Issue_Level": "WARN",
                    "Issue_Type": "Single Replica",
                    "Category": "Stability",
                    "Detail": "replicas=1",
                    "Recommendation": "Increase replicas > 1 for HA"
                })

        # Pod Spec Checks
        if kind == "Pod": # Standalone Pod? Not fetched mainly, but if we did.
             pod_spec = spec
        else:
             # Workload templates
             pod_spec = spec.get("template", {}).get("spec", {})
        
        check_pod_security(pod_spec, kind, name, ns, results, timestamp)

        containers = pod_spec.get("containers", [])
        container_issues = []
        for c in containers:
            check_resources(c, kind, name, ns, container_issues)
            check_probes(c, kind, name, ns, container_issues)
            check_image_tag(c, kind, name, ns, container_issues)
            check_security(c, kind, name, ns, container_issues)
        
        # Flatten container issues
        for issue in container_issues:
            results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": kind,
                "Name": name,
                **issue
            })
            
    return results

@app.post("/api/audit")
async def run_audit():
    """Runs the audit and returns the report."""
    try:
        raw_data = run_kubectl_get()
        report = audit_workloads(raw_data)
        
        # Optional: Save to CSV for record keeping if needed, but returning JSON is primary
        # We can implement GET /api/report to return the last run if we cache it, 
        # but the prompt implies integrating logic. Let's just return the data directly 
        # for simplicity or keep the GET /api/report pattern by caching in memory.
        
        # For simplicity and statelessness, we return the data here.
        # But Frontend expects GET /api/report separate from POST?
        # Frontend code: POST returns {status: success}, then GET /api/report
        # So we should store it.
        
        global last_report
        last_report = report
        
        return {"status": "success", "message": "Audit complete", "count": len(report)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# In-memory storage for simplicity
last_report = []

@app.get("/api/report")
async def get_report():
    return {"data": last_report}
