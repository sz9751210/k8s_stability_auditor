def check_finops_resources(container, kind, name, ns, issues):
    resources = container.get("resources", {})
    requests = resources.get("requests", {})
    
    req_cpu = requests.get("cpu", "0")
    if req_cpu.isdigit() and int(req_cpu) >= 4:
         issues.append({
            "Issue_Level": "WARN",
            "Issue_Type": "High Resource Request",
            "Category": "FinOps",
            "Detail": f"Container: {container['name']} requests {req_cpu} CPU",
            "Recommendation": "Review if this large allocation is efficiently used"
        })

def audit_finops_global(items, results, timestamp, exclude_ns):
    for item in items:
        kind = item.get("kind")
        meta = item.get("metadata", {})
        name = meta.get("name")
        ns = meta.get("namespace", "cluster")
        
        # Unused PV
        if kind == "PersistentVolume":
            status = item.get("status", {}).get("phase")
            if status == "Released":
                results.append({
                    "Timestamp": timestamp,
                    "Namespace": "cluster-scope",
                    "Type": "PersistentVolume",
                    "Name": name,
                    "Issue_Level": "WARN",
                    "Issue_Type": "Unused PV Cost",
                    "Category": "FinOps",
                    "Detail": "Status is Released",
                    "Recommendation": "Delete or Reclaim Volume"
                })
        
        # Unused LB
        if kind == "Service" and ns not in exclude_ns:
            spec = item.get("spec", {})
            if spec.get("type") == "LoadBalancer":
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
