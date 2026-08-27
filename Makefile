# AtlasTrip: five agents on five frameworks, talking over A2A.
#
# Run `make` on its own to see what is available.

CORE    := PYTHONPATH=packages/atlastrip_core/src packages/atlastrip_core/.venv/bin/python
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help install db seed reset run demo plan cards trail doctor test test-unit test-network lint diagrams clean

help:  ## Show this help
	@echo "AtlasTrip"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "  First run:  make install && make db && make seed && make run"
	@echo

install:  ## Create one virtualenv per service
	./scripts/install.sh

db:  ## Start Postgres in Docker and wait for it
	$(COMPOSE) up -d
	@printf "Waiting for Postgres"
	@for i in $$(seq 1 40); do \
	  if docker exec atlastrip-postgres pg_isready -U atlastrip -d atlastrip >/dev/null 2>&1; then \
	    echo " ready."; exit 0; fi; \
	  printf "."; sleep 1; done; \
	echo " timed out."; exit 1

seed:  ## Build the dataset in Postgres and TinyDB
	@./scripts/_unhide_pth.sh
	$(CORE) scripts/seed_data.py

reset: seed  ## Rebuild the dataset and wipe the audit trail
	@$(CORE) -c "from atlastrip_core import audit; audit.clear(); print('Audit trail cleared.')"

run:  ## Start the MCP server and all five agents (Ctrl-C to stop)
	./scripts/run_network.sh

demo:  ## Plan the sample trip against the running network
	@./scripts/_unhide_pth.sh
	@$(CORE) scripts/atlastrip.py plan

plan:  ## Plan a trip: make plan REQUEST="..."
	@./scripts/_unhide_pth.sh
	@$(CORE) scripts/atlastrip.py plan "$(REQUEST)"

cards:  ## Read every agent's card
	@./scripts/_unhide_pth.sh
	@$(CORE) scripts/atlastrip.py cards

trail:  ## Replay the A2A exchanges: make trail [CONTEXT=ctx-...]
	@./scripts/_unhide_pth.sh
	@$(CORE) scripts/atlastrip.py trail $(CONTEXT)

doctor:  ## Check Postgres, the MCP server and all five agents
	@./scripts/_unhide_pth.sh
	@$(CORE) scripts/atlastrip.py doctor

test: test-unit test-network  ## Run every test

test-unit:  ## Unit tests, each in its own agent's virtualenv
	./scripts/run_tests.sh

test-network:  ## Integration tests against the running network
	@./scripts/_unhide_pth.sh
	$(CORE) -m pytest tests/network -q

lint:  ## Lint every service with ruff
	uvx ruff check .

diagrams:  ## Regenerate the draw.io diagrams and their PNGs
	./scripts/export_diagrams.sh

clean:  ## Remove virtualenvs, logs and the Postgres volume
	rm -rf packages/*/.venv agents/*/.venv mcp_servers/*/.venv logs
	$(COMPOSE) down -v
