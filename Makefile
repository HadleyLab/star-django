.PHONY: restart

restart:
	docker compose -f compose.yaml stop
	docker compose -f compose.yaml pull
	docker compose -f compose.yaml up -d
