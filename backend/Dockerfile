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

COPY app /app/app

# We need to make sure we are in /app and pythonpath is correct, but since we copied into /app/app it might be weird.
# Best practice is to have backend/ as root.
# Let's assume WORKDIR /app.
# If we copy backend/app to /app/app.
# Then `uvicorn app.main:app` works.

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
