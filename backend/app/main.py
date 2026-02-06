from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import datetime
from app.auditor.core import run_kubectl_get, EXCLUDE_NS
from app.auditor.checks import stability, security, finops

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def audit_workloads(data):
    results = []
    items = data.get("items", [])
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 1. Global Checks (Cluster Scope or Cross-Resource)
    finops.audit_finops_global(items, results, timestamp, EXCLUDE_NS)
    stability.check_hpa_coverage(items, results, timestamp, EXCLUDE_NS)
    security.check_ingress_security(items, results, timestamp, EXCLUDE_NS)

    # 2. Per-Item Checks
    for item in items:
        metadata = item.get("metadata", {})
        ns = metadata.get("namespace", "default")
        name = metadata.get("name", "unknown")
        kind = item.get("kind", "unknown")
        
        # Skip resources handled globally or not targeted
        if kind in ["PersistentVolume", "Service", "HorizontalPodAutoscaler", "Ingress"]: continue

        if ns in EXCLUDE_NS:
            continue

        stability.check_replica_and_tag(item, kind, name, ns, results, timestamp)
        
        # Pod Spec logic
        spec = item.get("spec", {})
        if kind == "Pod":
             pod_spec = spec
        else:
             pod_spec = spec.get("template", {}).get("spec", {})
        
        security.check_host_access(pod_spec, kind, name, ns, results, timestamp)

        containers = pod_spec.get("containers", [])
        container_issues = []
        for c in containers:
            stability.check_resources(c, kind, name, ns, container_issues)
            stability.check_probes(c, kind, name, ns, container_issues)
            finops.check_finops_resources(c, kind, name, ns, container_issues)
            security.check_security_context(c, kind, name, ns, container_issues)
        
        # Flatten
        for issue in container_issues:
            results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": kind,
                "Name": name,
                **issue
            })
            
    return results

# In-memory storage
last_report = []

@app.post("/api/audit")
async def run_audit():
    try:
        raw_data = run_kubectl_get()
        report = audit_workloads(raw_data)
        global last_report
        last_report = report
        return {"status": "success", "message": "Audit complete", "count": len(report)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report")
async def get_report():
    return {"data": last_report}
