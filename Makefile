.PHONY: restart start stop update_statistics initialize_historical_counters

restart:
	docker compose -f compose.prod.yaml stop
	docker compose -f compose.prod.yaml pull
	docker compose -f compose.prod.yaml up -d

start:
	docker compose -f compose.prod.yaml pull

stop:
	docker compose -f compose.prod.yaml stop

collectstatic:
	docker compose -f compose.prod.yaml exec -i app python manage.py collectstatic --noinput

update_statistics:
	docker compose -f compose.prod.yaml exec -i app python manage.py update_statistic_cache

initialize_historical_counters:
	docker compose -f compose.prod.yaml exec -i app python manage.py initialize_historical_counters

initialize_historical_pmid_counters:
	docker compose -f compose.prod.yaml exec -i app python manage.py initialize_historical_pmid_counters.py
