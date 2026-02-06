from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import csv
import os
import json

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCRIPT_PATH = "/app/audit_k8s.sh"
REPORT_PATH = "/app/k8s_audit_report.csv"

@app.post("/api/audit")
async def run_audit():
    """Runs the shell script to generate the audit report."""
    if not os.path.exists(SCRIPT_PATH):
        raise HTTPException(status_code=500, detail="Audit script not found")
    
    try:
        # Run script, capture output
        result = subprocess.run([SCRIPT_PATH], capture_output=True, text=True)
        if result.returncode != 0:
            return {
                "status": "error",
                "message": "Audit script failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
        
        return {"status": "success", "message": "Audit complete", "output": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report")
async def get_report():
    """Reads the CSV report and returns it as JSON."""
    if not os.path.exists(REPORT_PATH):
        return {"data": []}
    
    data = []
    try:
        with open(REPORT_PATH, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
