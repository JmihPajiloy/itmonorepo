PYTHON ?= .venv/bin/python
TYPST ?= typst
RUN ?= verification/runs/new-run

.PHONY: setup experiments check check-stand report stop
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

experiments:
	$(PYTHON) run_stand.py --output-root "$(RUN)"

check:
	$(PYTHON) analyze.py
	$(PYTHON) analyze_media.py

check-stand:
	$(PYTHON) analyze.py --run-root "$(RUN)" --stand-only

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf

stop:
	docker compose stop
