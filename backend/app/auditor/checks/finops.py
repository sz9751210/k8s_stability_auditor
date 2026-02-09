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

    req_mem = requests.get("memory", "0")
    # Simple heuristic parsing: detect if Gi is present and value > 8
    # 8Gi, 8000Mi, etc.
    is_high_mem = False
    if req_mem.endswith("Gi"):
        try:
            val = float(req_mem.replace("Gi", ""))
            if val >= 8: is_high_mem = True
        except: pass
    elif req_mem.endswith("Mi"):
        try:
            val = float(req_mem.replace("Mi", ""))
            if val >= 8192: is_high_mem = True
        except: pass
        
    if is_high_mem:
        issues.append({
            "Issue_Level": "WARN",
            "Issue_Type": "High Memory Request",
            "Category": "FinOps",
            "Detail": f"Container: {container['name']} requests {req_mem}",
            "Recommendation": "Verify if >8GB memory is constantly needed"
        })

def check_namespace_quotas(items, results, timestamp, exclude_ns):
    quotas_ns = set()
    all_ns = set()
    
    for item in items:
        ns = item.get("metadata", {}).get("namespace")
        if ns: all_ns.add(ns)
        if item.get("kind") == "ResourceQuota":
            quotas_ns.add(ns)
            
    for ns in all_ns:
        if ns in exclude_ns: continue
        if ns not in quotas_ns:
             results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": "Namespace",
                "Name": ns,
                "Issue_Level": "WARN",
                "Issue_Type": "Missing ResourceQuota",
                "Category": "FinOps",
                "Detail": "No ResourceQuota found",
                "Recommendation": "Apply quotas to prevent cost overruns"
            })

def check_spot_suitability(items, results, timestamp, exclude_ns):
    # Map PDBs to Namespaces (simplification: PDBs target labels, but we'll assume existence in NS is a good proxy for now 
    # OR we can try to match selector. For simplicity/speed, let's match PDB targets)
    
    # Better approach: Check if PDB exists for the deployment.
    # We need to map Deployments -> Labels
    # PDB -> Selector
    
    # 1. Index PDBs by Namespace
    pdbs = {} # ns -> [selector_match_labels]
    
    for item in items:
        if item.get("kind") == "PodDisruptionBudget":
            ns = item.get("metadata", {}).get("namespace")
            selector = item.get("spec", {}).get("selector", {}).get("matchLabels", {})
            if ns not in pdbs: pdbs[ns] = []
            pdbs[ns].append(selector)
            
    # 2. Check Deployments
    for item in items:
        if item.get("kind") != "Deployment": continue
        
        ns = item.get("metadata", {}).get("namespace")
        if ns in exclude_ns: continue
        
        name = item.get("metadata", {}).get("name")
        spec = item.get("spec", {})
        replicas = spec.get("replicas", 1)
        labels = spec.get("selector", {}).get("matchLabels", {})
        
        # Spot Criteria:
        # - Replicas >= 3 (High Availability)
        # - Covered by PDB (Safe to drain)
        
        if replicas >= 3:
            # Check for PDB coverage
            covered = False
            if ns in pdbs:
                for pdb_selector in pdbs[ns]:
                    # Check if PDB selector is subset of Deployment labels
                    # Simplified matching: if PDB selector keys/values match deployment labels
                    if pdb_selector and all(labels.get(k) == v for k, v in pdb_selector.items()):
                        covered = True
                        break
            
            if covered:
                 results.append({
                    "Timestamp": timestamp,
                    "Namespace": ns,
                    "Type": "Deployment",
                    "Name": name,
                    "Issue_Level": "WARN", # Using WARN to highlight opportunity (Positive/Info level might be better, but we stick to schema)
                    "Issue_Type": "Spot Instance Candidate",
                    "Category": "FinOps",
                    "Detail": "HA (3+ Replicas) & PDB detected",
                    "Recommendation": "Migrate to Spot Nodes for ~60-90% savings"
                })

def audit_finops_global(items, results, timestamp, exclude_ns):
    check_namespace_quotas(items, results, timestamp, exclude_ns)
    check_spot_suitability(items, results, timestamp, exclude_ns)

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
