# =============================================================================
# Makefile — convenience tasks for Unix-friendly devs.
#
# WHY THIS EXISTS
#   `./build.sh` is the canonical full-build entry point. Make wraps the common
#   per-task commands so you can type `make test` instead of remembering the
#   per-stack incantation. It MUST stay in sync with build.sh and scripts/.
#
# Tabs matter in Makefiles. Recipes are tab-indented. Do not convert to spaces.
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help build run test test-jsonld test-seo-files test-conversion test-primary-ctas test-og test-assets test-anchors test-nginx test-form test-font-preload test-unit test-integration test-e2e lint fmt clean docker docker-run deploy

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Clean-clone -> running prerequisites met (delegates to build.sh)
	./build.sh

run: ## Run the service locally
	./scripts/run.sh

test: test-jsonld test-seo-files test-conversion test-primary-ctas test-og test-assets test-anchors test-nginx test-form test-font-preload ## Run all tests (stdlib-only smoke suite)

test-jsonld: ## Validate LocalBusiness JSON-LD parses + has required fields
	python tests/test_jsonld.py
	python tests/test_jsonld.py --selftest

test-seo-files: ## sitemap.xml + robots.txt parse; canonical origin agrees across index.html
	python tests/test_seo_files.py

test-conversion: ## CTA data-intent <-> INTENT_TO_TYPE <-> projectType radio contract holds
	python tests/test_conversion.py
	python tests/test_conversion.py --selftest

test-primary-ctas: ## Every primary "Request a bid" / btn-accent CTA carries data-intent; cta_click position emitted
	python tests/test_primary_ctas.py
	python tests/test_primary_ctas.py --selftest

test-og: ## OG + Twitter meta tags valid on index.html + 404.html; og:image = branded card
	python tests/test_og_twitter.py
	python tests/test_og_twitter.py --selftest

test-assets: ## Every JSON-LD/OG/Twitter image URL resolves to a real on-disk file w/ magic bytes
	python tests/test_assets.py
	python tests/test_assets.py --selftest

test-anchors: ## Every href="#..." resolves to a real id on the page; #contact ref-count above floor
	python tests/test_anchors.py
	python tests/test_anchors.py --selftest

test-nginx: ## nginx.conf: 5 security headers on server + every protected location, per-location Cache-Control
	python tests/test_nginx_headers.py
	python tests/test_nginx_headers.py --selftest

test-form: ## Intake form contract: Formspree action, required name/email/phone, honeypot, tel:<->JSON-LD phone agreement
	python tests/test_form.py
	python tests/test_form.py --selftest

test-font-preload: ## Google Fonts preload/stylesheet/noscript hrefs byte-identical on index + 404 (async pattern lock)
	python tests/test_font_preload.py
	python tests/test_font_preload.py --selftest

test-unit: ## Run unit tests only
	./scripts/test.sh unit

test-integration: ## Run integration tests only
	./scripts/test.sh integration

test-e2e: ## Run end-to-end tests (Selenium / Playwright)
	./scripts/test.sh e2e

lint: ## Lint + format check (no changes)
	./scripts/lint.sh

fmt: ## Lint + format with --fix
	./scripts/lint.sh --fix

clean: ## Remove build artifacts and caches
	rm -rf .venv node_modules bin obj dist build .pytest_cache __pycache__ htmlcov

docker: ## Build Docker image
	docker build -t $(shell basename $(CURDIR)):local .

docker-run: ## Run Docker image with local .env
	docker run --rm -p 8000:8000 --env-file .env $(shell basename $(CURDIR)):local

deploy: ## Deploy to the platform configured in scripts/deploy.sh
	./scripts/deploy.sh
