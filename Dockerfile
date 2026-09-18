FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime bootstrap builds the public-data catalog only when no healthy local catalog exists.
# The static GitHub Pages demo does not depend on this container.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python scripts/bootstrap_runtime.py && uvicorn src.app:app --host 0.0.0.0 --port ${PORT}"]
