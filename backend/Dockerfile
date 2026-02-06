FROM python:3.11-slim

# Install dependencies: curl, kubectl, jq
RUN apt-get update && apt-get install -y curl jq && \
    ARCH="$(dpkg --print-architecture)" && \
    K8S_RELEASE="$(curl -L -s https://dl.k8s.io/release/stable.txt)" && \
    curl -LO "https://dl.k8s.io/release/${K8S_RELEASE}/bin/linux/${ARCH}/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY main.py .

# We wait to mount the script via volume or copy it now? 
# The plan implies script is in root. We should copy it into container.
# In docker-compose context context might be different, but let's assume root context or copy relevant files.
# For simplicity, we assume build context will allow accessing script, OR we mount it.
# To be safe for standalone build, let's assume we copy it from potential context, but 
# standard docker compose usually builds from subdirectory.
# We will handle this in docker-compose.yml by setting context to root or copying script.
# For now, let's assume the build context is the `backend` folder? 
# If context is backend folder, we can't access `../audit_k8s.sh` easily without context adjustment.
# WE WILL SET CONTEXT TO ROOT in docker-compose.

# Just in case, we will rely on VOLUME mount or docker compose logic.
# But for 'Standard' Dockerfile, let's copy it if it exists in current dir.
# Actually, better to just rely on volume in Compose or Copy in root context.

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
