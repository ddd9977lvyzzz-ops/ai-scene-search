.PHONY: run test eval verify posters rebuild docker

run:
	PYTHONPATH=. uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

test:
	PYTHONPATH=. python -m pytest -q

eval:
	PYTHONPATH=. python scripts/run_eval_suite.py

verify:
	PYTHONPATH=. python scripts/verify_catalog.py --db db/catalog.sqlite3 --min-records 1000

posters:
	PYTHONPATH=. python scripts/backfill_real_posters.py --db db/catalog.sqlite3 --strict

rebuild:
	PYTHONPATH=. python scripts/backfill_real_posters.py --db db/catalog.sqlite3 --strict
	PYTHONPATH=. python scripts/recompute_tags.py
	PYTHONPATH=. python scripts/migrate_content_intelligence.py
	PYTHONPATH=. python scripts/migrate_evidence_corpus.py
	PYTHONPATH=. python scripts/build_embeddings.py --dim 128
	PYTHONPATH=. python scripts/run_eval_suite.py

docker:
	docker build -t ai-scene-search .
