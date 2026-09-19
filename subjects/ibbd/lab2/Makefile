TYPST ?= typst

.PHONY: help check report

help:
	@printf '%s\n' 'make check  - rebuild PostgreSQL DB workshop and save verification output' 'make report - build report.pdf'

check:
	./check.sh

report:
	$(TYPST) compile --root ../../.. report.typ report.pdf
