FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170

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

