def check_resources(container, kind, name, ns, issues):
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

def check_probes(container, kind, name, ns, issues):
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

def check_replica_and_tag(item, kind, name, ns, results, timestamp):
    spec = item.get("spec", {})
    
    # Replica Check
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
            
    # Tag Check
    pod_spec = spec.get("template", {}).get("spec", {}) if kind != "Pod" else spec
    for c in pod_spec.get("containers", []):
         image = c.get("image", "")
         if image.endswith(":latest") or ":" not in image:
            results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": kind,
                "Name": name,
                "Issue_Level": "WARN",
                "Issue_Type": "Using Latest Tag",
                "Category": "Stability",
                "Detail": f"Container: {c['name']} ({image})",
                "Recommendation": "Use specific version tag"
            })

def check_hpa_coverage(items, results, timestamp, exclude_ns):
    """Check if deployments have HPA."""
    # Build set of targeted deployments
    hpa_targets = set() 
    deployments = []
    
    for item in items:
        kind = item.get("kind")
        ns = item.get("metadata", {}).get("namespace")
        name = item.get("metadata", {}).get("name")
        
        if ns in exclude_ns: continue
        
        if kind == "HorizontalPodAutoscaler":
             target = item.get("spec", {}).get("scaleTargetRef", {})
             if target.get("kind") == "Deployment":
                 hpa_targets.add(f"{ns}/{target.get('name')}")
        elif kind == "Deployment":
             deployments.append((ns, name))
             
    for ns, name in deployments:
        if f"{ns}/{name}" not in hpa_targets:
             results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": "Deployment",
                "Name": name,
                "Issue_Level": "WARN",
                "Issue_Type": "Missing HPA",
                "Category": "Stability",
                "Detail": "No HPA targeting this deployment",
                "Recommendation": "Configure HPA for auto-scaling"
            })
