PYTHON ?= python3
TYPST ?= typst
.PHONY: check report
check:
	$(PYTHON) check.py

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf
