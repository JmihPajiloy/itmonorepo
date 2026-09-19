PYTHON ?= python3
TYPST ?= typst

.PHONY: check report

check:
	$(PYTHON) verify.py

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf

