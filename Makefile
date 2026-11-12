# Cloud Cost Tracker
#   make run      - run in the foreground (Ctrl+C to quit)
#   make start    - run in the background
#   make stop     - stop the background server (or whatever is on PORT)
#   make help     - list everything

PORT    ?= 8000
HOST    ?= 127.0.0.1
BACKEND := backend
RUN_DIR := .run
PIDFILE := $(RUN_DIR)/server.pid
LOGFILE := $(RUN_DIR)/server.log
SERVE   := uv run cost-tracker serve --host $(HOST) --port $(PORT)

.DEFAULT_GOAL := help
.PHONY: help install run dev start stop restart status logs open test lint report email

help: ## Show this help
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd $(BACKEND) && uv sync

run: ## Run the dashboard in the foreground
	cd $(BACKEND) && $(SERVE)

dev: ## Run in the foreground with auto-reload
	cd $(BACKEND) && $(SERVE) --reload

start: ## Start the dashboard in the background
	@mkdir -p $(RUN_DIR); \
	if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "Already running (pid $$(cat $(PIDFILE))) at http://$(HOST):$(PORT)"; exit 0; fi; \
	if lsof -ti tcp:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Port $(PORT) is already in use. Run 'make stop' or use PORT=8001."; exit 1; fi; \
	(cd $(BACKEND) && nohup $(SERVE) > ../$(LOGFILE) 2>&1 & echo $$! > $(PIDFILE)); \
	for i in $$(seq 1 30); do \
		curl -sf http://$(HOST):$(PORT)/api/health >/dev/null && break; sleep 0.5; done; \
	if curl -sf http://$(HOST):$(PORT)/api/health >/dev/null; then \
		echo "Running at http://$(HOST):$(PORT) (pid $$(cat $(PIDFILE)), logs: make logs)"; \
	else echo "Failed to start. Last log lines:"; tail -20 $(LOGFILE); exit 1; fi

stop: ## Stop the background dashboard (and anything else on PORT)
	@pids=""; \
	if [ -f $(PIDFILE) ]; then pids="$$(cat $(PIDFILE)) $$(pgrep -P $$(cat $(PIDFILE)) 2>/dev/null)"; fi; \
	pids="$$pids $$(lsof -ti tcp:$(PORT) -sTCP:LISTEN 2>/dev/null)"; \
	pids=$$(echo $$pids | tr ' ' '\n' | sort -u | xargs); \
	alive=""; for p in $$pids; do kill -0 $$p 2>/dev/null && alive="$$alive $$p"; done; \
	if [ -z "$$alive" ]; then echo "Not running"; rm -f $(PIDFILE); exit 0; fi; \
	kill $$alive 2>/dev/null; \
	for i in $$(seq 1 20); do lsof -ti tcp:$(PORT) -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 0.25; done; \
	left=$$(lsof -ti tcp:$(PORT) -sTCP:LISTEN 2>/dev/null); \
	if [ -n "$$left" ]; then kill -9 $$left 2>/dev/null; fi; \
	rm -f $(PIDFILE); echo "Stopped (pid$$alive)"

restart: stop start ## Restart the background dashboard

status: ## Show whether the dashboard is running
	@if curl -sf http://$(HOST):$(PORT)/api/health >/dev/null; then \
		echo "Running at http://$(HOST):$(PORT) (pid $$(lsof -ti tcp:$(PORT) -sTCP:LISTEN | tr '\n' ' '))"; \
	else echo "Not running"; fi

logs: ## Follow the background server's log
	@tail -f $(LOGFILE)

open: ## Open the dashboard in your browser
	open http://$(HOST):$(PORT)

test: ## Run the test suite
	cd $(BACKEND) && uv run pytest

lint: ## Run pylint
	cd $(BACKEND) && uv run pylint src

report: ## Print the monthly cost report
	cd $(BACKEND) && uv run cost-tracker report

email: ## Print and email the monthly cost report
	cd $(BACKEND) && uv run cost-tracker report --email
