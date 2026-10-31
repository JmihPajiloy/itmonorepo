.PHONY: check report

check:
	python3 check.py

report: check
	typst compile --root ../../.. report.typ report.pdf
