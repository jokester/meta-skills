# venv is fully managed by this Makefile (pattern copied from vibra/py).
# Never `pip install` by hand, never activate the venv manually.

default: deps
	@echo "deps installed"

###
### SECTION dev scripts
###

PY_CODE_ROOTS = src/

format-py:
	venv/bin/ruff format $(PY_CODE_ROOTS)

lint-py:
	venv/bin/ruff check $(PY_CODE_ROOTS)

test: deps
	venv/bin/pytest $(PY_CODE_ROOTS)

###
### SECTION deps
###

PYTHON_VER ?= 3.13

REQUIREMENTS = -r requirements.txt --editable .
UV_PIP_INSTALL = UV_PYTHON=venv UV_LINK_MODE=symlink uv pip install

deps: Makefile venv/.deps_installed

venv/.deps_installed: venv/.venv_created requirements.txt pyproject.toml
	$(UV_PIP_INSTALL) $(REQUIREMENTS)
	@echo "deps installed"
	@touch $@

venv: venv/.venv_created

venv/.venv_created: Makefile
	uv venv --clear --python=$(PYTHON_VER) venv
	@touch $@
	@rm -fv venv/.deps_installed

.PHONY: default format-py lint-py test deps venv
