.PHONY: run frontend check ruff database lint api start-all stop-all status clean-cache worker worker-start worker-stop worker-restart warmup
.PHONY: docker-buildx-prepare docker-buildx-clean docker-buildx-reset
.PHONY: docker-push docker-push-latest docker-release docker-build-local tag export-docs

# Get version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)
UV_RUN := uv run --no-sync --env-file .env
STARTUP_TIMEOUT ?= 120
STARTUP_POLL_INTERVAL ?= 1
API_HEALTH_URL ?= http://127.0.0.1:5055/health
FRONTEND_DEV_FLAGS ?= --webpack --disable-source-maps
WARMUP_URL_BASE ?= http://127.0.0.1:3000
WARMUP_ROUTES ?= / /sources /notebooks /search /podcasts /transformations /settings /settings/api-keys /advanced
WARMUP_WAIT_TIMEOUT ?= 90
AUTO_WARMUP ?= 0

# Image names for both registries
DOCKERHUB_IMAGE := podcast-geeker/podcast-geeker
GHCR_IMAGE := ghcr.io/podcast-geeker/podcast-geeker

# Build platforms
PLATFORMS := linux/amd64,linux/arm64

database:
	docker compose -f examples/docker-compose-dev.yml up -d surrealdb

run:
	@echo "⚠️  Warning: Starting frontend only. For full functionality, use 'make start-all'"
	@if [ "$(AUTO_WARMUP)" = "1" ]; then \
		( $(MAKE) -s warmup >/dev/null 2>&1 || true ) & \
	fi
	cd frontend && npm run dev -- $(FRONTEND_DEV_FLAGS)

frontend:
	@if [ "$(AUTO_WARMUP)" = "1" ]; then \
		( $(MAKE) -s warmup >/dev/null 2>&1 || true ) & \
	fi
	cd frontend && npm run dev -- $(FRONTEND_DEV_FLAGS)

lint:
	uv run python -m mypy .

ruff:
	ruff check . --fix

# === Docker Build Setup ===
docker-buildx-prepare:
	@docker buildx inspect multi-platform-builder >/dev/null 2>&1 || \
		docker buildx create --use --name multi-platform-builder --driver docker-container
	@docker buildx use multi-platform-builder

docker-buildx-clean:
	@echo "🧹 Cleaning up buildx builders..."
	@docker buildx rm multi-platform-builder 2>/dev/null || true
	@docker ps -a | grep buildx_buildkit | awk '{print $$1}' | xargs -r docker rm -f 2>/dev/null || true
	@echo "✅ Buildx cleanup complete!"

docker-buildx-reset: docker-buildx-clean docker-buildx-prepare
	@echo "✅ Buildx reset complete!"

# === Docker Build Targets ===

# Build production image for local platform only (no push)
docker-build-local:
	@echo "🔨 Building production image locally ($(shell uname -m))..."
	docker build \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):local \
		.
	@echo "✅ Built $(DOCKERHUB_IMAGE):$(VERSION) and $(DOCKERHUB_IMAGE):local"
	@echo "Run with: docker run -p 5055:5055 -p 3000:3000 $(DOCKERHUB_IMAGE):local"

# Build and push version tags ONLY (no latest) for both regular and single images
docker-push: docker-buildx-prepare
	@echo "📤 Building and pushing version $(VERSION) to both registries..."
	@echo "🔨 Building regular image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):$(VERSION) \
		--push \
		.
	@echo "🔨 Building single-container image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		--push \
		.
	@echo "✅ Pushed version $(VERSION) to both registries (latest NOT updated)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION)"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single"

# Update v1-latest tags to current version (both regular and single images)
docker-push-latest: docker-buildx-prepare
	@echo "📤 Updating v1-latest tags to version $(VERSION)..."
	@echo "🔨 Building regular image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):v1-latest \
		-t $(GHCR_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):v1-latest \
		--push \
		.
	@echo "🔨 Building single-container image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(DOCKERHUB_IMAGE):v1-latest-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):v1-latest-single \
		--push \
		.
	@echo "✅ Updated v1-latest to version $(VERSION)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single → v1-latest-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single → v1-latest-single"

# Full release: push version AND update latest tags
docker-release: docker-push-latest
	@echo "✅ Full release complete for version $(VERSION)"

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"


dev:
	docker compose -f docker-compose.dev.yml up --build 

full:
	docker compose -f docker-compose.full.yml up --build 


api:
	$(UV_RUN) run_api.py

.PHONY: worker worker-start worker-stop worker-restart

worker: worker-start

worker-start:
	@echo "Starting surreal-commands worker..."
	$(UV_RUN) surreal-commands-worker --import-modules commands

worker-stop:
	@echo "Stopping surreal-commands worker..."
	pkill -f "surreal-commands-worker" || true

worker-restart: worker-stop
	@sleep 2
	@$(MAKE) worker-start

# === Service Management ===
start-all:
	@echo "🚀 Starting Podcast Geeker (Database + API + Worker + Frontend)..."
	@echo "🧽 Cleaning stale local processes..."
	@pkill -f "run_api.py" >/dev/null 2>&1 || true
	@pkill -f "uvicorn api.main:app" >/dev/null 2>&1 || true
	@pkill -f "surreal-commands-worker" >/dev/null 2>&1 || true
	@pkill -f "next dev" >/dev/null 2>&1 || true
	@echo "📊 Starting SurrealDB..."
	@docker compose -f examples/docker-compose-dev.yml up -d surrealdb
	@echo "⏳ Waiting for SurrealDB on :8000..."
	@timeout=$(STARTUP_TIMEOUT); \
	while ! nc -z 127.0.0.1 8000 >/dev/null 2>&1; do \
		if [ $$timeout -le 0 ]; then \
			echo "❌ SurrealDB did not become ready within $(STARTUP_TIMEOUT)s"; \
			exit 1; \
		fi; \
		sleep $(STARTUP_POLL_INTERVAL); \
		timeout=$$((timeout-$(STARTUP_POLL_INTERVAL))); \
	done
	@echo "✅ SurrealDB is ready"
	@echo "🔧 Starting API backend..."
	@API_RELOAD=$${API_RELOAD:-false} $(UV_RUN) run_api.py &
	@echo "⏳ Waiting for API health endpoint..."
	@timeout=$(STARTUP_TIMEOUT); \
	while ! curl -fsS $(API_HEALTH_URL) >/dev/null 2>&1; do \
		if [ $$timeout -le 0 ]; then \
			echo "❌ API did not become ready within $(STARTUP_TIMEOUT)s ($(API_HEALTH_URL))"; \
			exit 1; \
		fi; \
		sleep $(STARTUP_POLL_INTERVAL); \
		timeout=$$((timeout-$(STARTUP_POLL_INTERVAL))); \
	done
	@echo "✅ API is ready"
	@echo "⚙️ Starting background worker..."
	@$(UV_RUN) surreal-commands-worker --import-modules commands &
	@echo "⏳ Waiting for worker process..."
	@timeout=$(STARTUP_TIMEOUT); \
	while ! pgrep -f "surreal-commands-worker" >/dev/null; do \
		if [ $$timeout -le 0 ]; then \
			echo "❌ Worker did not become ready within $(STARTUP_TIMEOUT)s"; \
			exit 1; \
		fi; \
		sleep $(STARTUP_POLL_INTERVAL); \
		timeout=$$((timeout-$(STARTUP_POLL_INTERVAL))); \
	done
	@echo "✅ Worker is running"
	@echo "🌐 Starting Next.js frontend..."
	@echo "✅ All services started!"
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔗 API: http://localhost:5055"
	@echo "📚 API Docs: http://localhost:5055/docs"
	@if [ "$(AUTO_WARMUP)" = "1" ]; then \
		( $(MAKE) -s warmup >/dev/null 2>&1 || true ) & \
	fi
	cd frontend && npm run dev -- $(FRONTEND_DEV_FLAGS)

stop-all:
	@echo "🛑 Stopping all Podcast Geeker services..."
	@pkill -f "next dev" || true
	@pkill -f "surreal-commands-worker" || true
	@pkill -f "run_api.py" || true
	@pkill -f "uvicorn api.main:app" || true
	@docker compose down
	@echo "✅ All services stopped!"

status:
	@echo "📊 Podcast Geeker Service Status:"
	@echo "Database (SurrealDB):"
	@docker compose ps surrealdb 2>/dev/null || echo "  ❌ Not running"
	@echo "API Backend:"
	@pgrep -f "run_api.py\|uvicorn api.main:app" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Background Worker:"
	@pgrep -f "surreal-commands-worker" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Next.js Frontend:"
	@pgrep -f "next dev" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"

warmup:
	@echo "🔥 Warming up frontend routes on $(WARMUP_URL_BASE)..."
	@timeout=$(WARMUP_WAIT_TIMEOUT); \
	while ! curl -fsS -o /dev/null "$(WARMUP_URL_BASE)/"; do \
		if [ $$timeout -le 0 ]; then \
			echo "❌ Frontend is not reachable at $(WARMUP_URL_BASE)"; \
			exit 1; \
		fi; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done
	@for route in $(WARMUP_ROUTES); do \
		echo "  → $$route"; \
		curl -fsS -o /dev/null "$(WARMUP_URL_BASE)$$route" || { \
			echo "❌ Warmup failed for $$route (is frontend running?)"; \
			exit 1; \
		}; \
	done
	@echo "✅ Warmup complete"

# === Documentation Export ===
export-docs:
	@echo "📚 Exporting documentation..."
	@uv run python scripts/export_docs.py
	@echo "✅ Documentation export complete!"

# === Cleanup ===
clean-cache:
	@echo "🧹 Cleaning cache directories..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -type f -delete 2>/dev/null || true
	@find . -name "*.pyo" -type f -delete 2>/dev/null || true
	@find . -name "*.pyd" -type f -delete 2>/dev/null || true
	@echo "✅ Cache directories cleaned!"