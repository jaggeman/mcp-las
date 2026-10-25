FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

WORKDIR /app

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY . .

# Säkerhetshärdning: Kör som icke-root användare
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV PYTHONPATH=/app
ENV FIREBASE_PROJECT_ID=paygap-prod
ENV EMBEDDING_PROVIDER=mock

EXPOSE 8080

CMD ["python", "-m", "src.server"]

