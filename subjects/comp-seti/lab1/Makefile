PYTHON ?= .venv/bin/python
TYPST ?= typst

.PHONY: setup check report

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

check:
	$(PYTHON) generate.py >/dev/null

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf
