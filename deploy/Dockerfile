FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/onyx
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
COPY web/backend/requirements.txt ./web/backend/requirements.txt
RUN pip install --no-cache-dir -r web/backend/requirements.txt
COPY . .
RUN useradd --system --uid 10001 --home /opt/onyx onyx && mkdir -p /var/lib/onyx && chown -R onyx:onyx /opt/onyx/web/backend /var/lib/onyx
USER onyx
EXPOSE 8020
CMD ["python", "-m", "uvicorn", "web.backend.server:app", "--host", "0.0.0.0", "--port", "8020", "--proxy-headers", "--forwarded-allow-ips", "172.16.0.0/12"]
