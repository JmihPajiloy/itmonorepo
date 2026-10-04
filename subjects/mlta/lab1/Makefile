.PHONY: check report

PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

check:
	$(PYTHON) diagrams/generate.py
	@test -f report.typ
	@printf '%s\n' 'Разбиения колоды проверены; схемы пересобраны.'

report:
	$(PYTHON) diagrams/generate.py
	typst compile --root ../../.. report.typ report.pdf
