.PHONY: check report

check:
	python3 network.py
	@test -f report.typ

report: check
	typst compile --root ../../.. report.typ report.pdf
