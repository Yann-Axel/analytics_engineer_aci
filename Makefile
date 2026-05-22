# Convenience targets so reviewers don't have to memorise docker compose flags.
# All real work happens in docker-compose.yml; this file is just shortcuts.

.DEFAULT_GOAL := help

.PHONY: help build pipeline dashboard mcp docs shell clean reset

help:                ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build:               ## Build the Docker image.
	docker compose build

pipeline:            ## Run the full pipeline (load → generate → dbt build → validate).
	docker compose run --rm pipeline

dashboard:           ## Start the Streamlit dashboard at http://localhost:8501.
	docker compose up dashboard

mcp:                 ## Run the MCP server interactively (stdio).
	docker compose run --rm -i mcp

docs:                ## Serve auto-generated dbt docs at http://localhost:8080.
	docker compose --profile docs up dbt-docs

shell:               ## Open a bash shell in a fresh container with /app mounted.
	docker compose run --rm pipeline bash

clean:               ## Remove containers but keep the image and the data volume.
	docker compose down

reset:               ## Nuke everything: containers, image, and the local warehouse.
	docker compose down --rmi local --volumes
	rm -f data/aci.duckdb data/aci.duckdb.wal
	rm -rf dbt_project/target dbt_project/logs
