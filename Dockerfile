FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# The repository keeps a portable 3,339-title JSON corpus. Rebuild the SQLite + 128d LSA index inside the image.
RUN python scripts/bootstrap_catalog.py --source site/catalog.min.json --db db/catalog.sqlite3 --model db/embedding_model.joblib \
 && python scripts/verify_catalog.py --db db/catalog.sqlite3 --min-records 1000 --min-china-series 150
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
