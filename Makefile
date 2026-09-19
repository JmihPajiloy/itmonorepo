.PHONY: help check report

help:
	@printf '%s\n' 'make check SUBJECT=ibbd LAB=lab1' 'make report SUBJECT=ibbd LAB=lab1'

check report:
	$(if $(and $(SUBJECT),$(LAB)),,$(error Specify SUBJECT and LAB; see make help))
	$(MAKE) -C "subjects/$(SUBJECT)/$(LAB)" $@
