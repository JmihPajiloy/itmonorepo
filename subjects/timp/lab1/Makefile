PYTHON ?= python3
NODE ?= node
TYPST ?= typst
.PHONY: check report
check:
	$(PYTHON) check.py
	$(NODE) check_web.mjs

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf
