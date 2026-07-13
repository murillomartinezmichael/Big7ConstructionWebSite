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
.PHONY: help build run test test-jsonld test-seo-files test-conversion test-primary-ctas test-url-prefill test-og test-assets test-anchors test-nginx test-form test-font-preload test-images test-breadcrumbs test-service-schema test-offer-catalog test-dockerfile test-meta-descriptions test-intake-analytics test-a11y-baseline test-unit test-integration test-e2e lint fmt clean docker docker-run deploy

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Clean-clone -> running prerequisites met (delegates to build.sh)
	./build.sh

run: ## Run the service locally
	./scripts/run.sh

test: test-jsonld test-seo-files test-conversion test-primary-ctas test-url-prefill test-og test-assets test-anchors test-nginx test-form test-font-preload test-images test-breadcrumbs test-service-schema test-offer-catalog test-dockerfile test-meta-descriptions test-intake-analytics test-a11y-baseline ## Run all tests (stdlib-only smoke suite)

test-jsonld: ## LocalBusiness JSON-LD parses + required fields; FAQPage Q.name agrees with visible <summary> text in order (schema/page drift lock)
	python tests/test_jsonld.py
	python tests/test_jsonld.py --selftest

test-seo-files: ## sitemap.xml + robots.txt parse; canonical origin agrees; every <loc> on disk; every indexable *.html listed
	python tests/test_seo_files.py
	python tests/test_seo_files.py --selftest

test-conversion: ## CTA data-intent <-> INTENT_TO_TYPE <-> projectType radio contract holds; lane-page deep-link intents + src attribution locked
	python tests/test_conversion.py
	python tests/test_conversion.py --selftest

test-primary-ctas: ## Every primary "Request a bid" / btn-accent CTA carries data-intent; cta_click position emitted
	python tests/test_primary_ctas.py
	python tests/test_primary_ctas.py --selftest

test-url-prefill: ## URL-param prefill IIFE: SAFE_PARAM whitelist gates params before DOM; landing_prefill emitted; utm_source accepted
	python tests/test_url_prefill.py
	python tests/test_url_prefill.py --selftest

test-og: ## OG + Twitter meta tags valid on all 6 top-level HTMLs; og:image = branded card; <link rel="canonical"> agrees with og:url on 5 indexable pages, absent on 404
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

test-images: ## <img> contract: WCAG 1.1.1 alt, images/ src on disk, hero fp=high <-> preload href agree, lazy paired with async decode
	python tests/test_images.py
	python tests/test_images.py --selftest

test-breadcrumbs: ## BreadcrumbList JSON-LD on the three lane pages: parses, Home > Lane, canonical origin agrees
	python tests/test_breadcrumbs.py
	python tests/test_breadcrumbs.py --selftest

test-service-schema: ## Service JSON-LD on the three lane pages: provider points at Big 7 LocalBusiness, areaServed populated
	python tests/test_service_schema.py
	python tests/test_service_schema.py --selftest

test-offer-catalog: ## Parent GeneralContractor `hasOfferCatalog` mirrors three-lane IA; each nested OfferCatalog.url == the lane page's Service.url (drift lock)
	python tests/test_offer_catalog.py
	python tests/test_offer_catalog.py --selftest

test-dockerfile: ## Dockerfile-vs-repo drift lock: every root *.html has a matching COPY line into /usr/share/nginx/html/
	python tests/test_dockerfile_html.py
	python tests/test_dockerfile_html.py --selftest

test-meta-descriptions: ## <meta name="description"> present on every top-level page, length [40, 220], unique across pages, not identical to <title>
	python tests/test_meta_descriptions.py
	python tests/test_meta_descriptions.py --selftest

test-intake-analytics: ## cta_click + intake_submit payload keys locked; has_prefill derived from PREFILL_MARK; message_length uses .trim().length; submit listener capture=true
	python tests/test_intake_analytics.py
	python tests/test_intake_analytics.py --selftest

test-a11y-baseline: ## LAW 11 baseline across 6 top-level pages: lang=en, skip-link -> #main, <main> landmark, prefers-reduced-motion, :focus-visible, /accessibility link
	python tests/test_a11y_baseline.py
	python tests/test_a11y_baseline.py --selftest

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
