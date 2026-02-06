def check_security_context(container, kind, name, ns, issues):
    security_context = container.get("securityContext", {})
    
    if security_context.get("privileged") is True:
        issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Privileged Container",
            "Category": "Security",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Avoid privileged mode"
        })
        
    if security_context.get("runAsUser") == 0:
         issues.append({
            "Issue_Level": "HIGH",
            "Issue_Type": "Runs as Root",
            "Category": "Security",
            "Detail": f"Container: {container['name']}",
            "Recommendation": "Set runAsUser to non-zero"
        })
    
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

def check_host_access(spec, kind, name, ns, results, timestamp):
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
            "Recommendation": "Disable hostNetwork"
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

def check_ingress_security(items, results, timestamp, exclude_ns):
    for item in items:
        if item.get("kind") != "Ingress": continue
        
        ns = item.get("metadata", {}).get("namespace")
        name = item.get("metadata", {}).get("name")
        if ns in exclude_ns: continue
        
        spec = item.get("spec", {})
        tls = spec.get("tls", [])
        
        if not tls:
             results.append({
                "Timestamp": timestamp,
                "Namespace": ns,
                "Type": "Ingress",
                "Name": name,
                "Issue_Level": "HIGH",
                "Issue_Type": "Missing TLS",
                "Category": "Security",
                "Detail": "Ingress has no TLS configuration",
                "Recommendation": "Enable TLS for secure access"
            })
