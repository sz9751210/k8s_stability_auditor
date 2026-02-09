
import sys
import os
import json

# Add parent dir to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.auditor.checks import stability, finops, security

def test_audit_logic():
    print("Running Audit Logic Verification...")
    
    # Mock Data
    mock_items = [
        # 1. Spot Candidate: Deployment with 3 replicas + PDB
        {
            "kind": "Deployment",
            "metadata": {"name": "spot-ready", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "selector": {"matchLabels": {"app": "spot-ready"}}
            }
        },
        {
            "kind": "PodDisruptionBudget",
            "metadata": {"name": "spot-pdb", "namespace": "default"},
            "spec": {"selector": {"matchLabels": {"app": "spot-ready"}}}
        },
        # 2. Memory Hog: Container with 10Gi Request
        {
            "kind": "Deployment",
            "metadata": {"name": "mem-hog", "namespace": "default"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "hog",
                                "resources": {"requests": {"memory": "10Gi"}}
                            }
                        ]
                    }
                }
            }
        },
        # 3. Missing NetworkPolicy (Namespace exists, but no policy)
        # Note: Logic discovers namespaces from resources. Add a resource in 'open-ns'.
        {
            "kind": "Pod", 
            "metadata": {"name": "exposed-pod", "namespace": "open-ns"}
        }
    ]

    results = []
    timestamp = "2023-01-01T00:00:00Z"
    exclude_ns = ["kube-system"]

    # Run Checks
    finops.check_spot_suitability(mock_items, results, timestamp, exclude_ns)
    finops.audit_finops_global(mock_items, results, timestamp, exclude_ns) 
    # Note: audit_finops_global calls check_spot_suitability and check_namespace_quotas internally in my implementation?
    # Let's check main.py or just call individual functions if I want unit precision.
    # In main.py: 
    # finops.audit_finops_global(items, results, timestamp, EXCLUDE_NS)
    # stability.check_hpa_coverage...
    # security.check_network_policies...

    # Let's call the specific checks we added
    security.check_network_policies(mock_items, results, timestamp, exclude_ns)
    
    # Check individual items for memory checks
    for item in mock_items:
        if item.get("kind") == "Deployment":
            # stability/finops per-item logic usually iterates containers
            tpl = item.get("spec", {}).get("template", {}).get("spec", {})
            for c in tpl.get("containers", []):
                finops.check_finops_resources(c, "Deployment", item["metadata"]["name"], item["metadata"]["namespace"], results)

    # Assertions
    spot_found = any(r["Issue_Type"] == "Spot Instance Candidate" and r["Name"] == "spot-ready" for r in results)
    mem_found = any(r["Issue_Type"] == "High Memory Request" and "10Gi" in r["Detail"] for r in results)
    policy_found = any(r["Issue_Type"] == "Missing NetworkPolicy" and r["Namespace"] == "open-ns" for r in results)

    print(f"Spot Candidate Detection: {'PASS' if spot_found else 'FAIL'}")
    print(f"Memory Hog Detection:     {'PASS' if mem_found else 'FAIL'}")
    print(f"Missing NetPol Detection: {'PASS' if policy_found else 'FAIL'}")

    if not (spot_found and mem_found and policy_found):
        print("Dumping Results for Debug:")
        print(json.dumps(results, indent=2))
        sys.exit(1)
    
    print("All Logic Checks Passed!")

if __name__ == "__main__":
    test_audit_logic()
