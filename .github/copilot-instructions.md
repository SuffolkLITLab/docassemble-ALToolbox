# ALToolbox for Docassemble

ALToolbox is a Python package that provides utility functions, web components, and templates for Docassemble legal document automation interviews. It's part of the Suffolk University Law School LIT Lab's Document Assembly Line project.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Quick Setup (No Full Testing)
For basic development work without running the full test suite:
- `pip install -e .` -- installs package in development mode. Takes 5-10 seconds when network is available. FAILS with timeout errors in restricted network environments (this is EXPECTED).
- `black --check .` -- checks code formatting. Takes 0.5 seconds.
- `python setup.py check` -- validates package metadata. Takes 0.2 seconds.
- Basic import test: `python -c "import docassemble.ALToolbox; print(docassemble.ALToolbox.__version__)"`

### Full Development Environment
For complete testing and development (requires docassemble framework):
- `sudo apt-get update && sudo apt-get -y install libcurl4-openssl-dev build-essential python3-dev libldap2-dev libsasl2-dev slapd ldap-utils tox lcov libzbar0 libaugeas0 augeas-lenses`
- `python -m venv venv`
- `source venv/bin/activate`
- `pip install wheel`
- `pip install -v -r docassemble/ALToolbox/requirements.txt` -- installs docassemble framework and dependencies. Takes 5-15 minutes. NEVER CANCEL. Set timeout to 20+ minutes.
- `pip install -v --editable .` -- installs package in development mode
- `export PYTHONPATH=$PYTHONPATH:$PWD`

### Running Tests
CRITICAL: Tests require the full docassemble framework to run.
- `python -m mypy . --exclude '^build/' --explicit-package-bases` -- runs type checking. Takes 10-30 seconds. NEVER CANCEL.
- Temporarily move namespace init: `mv docassemble/__init__.py docassemble/__init__.py.bak` (if it exists)
- `python -m unittest discover docassemble` -- runs all unit tests. Takes 30-60 seconds. NEVER CANCEL. Set timeout to 90+ seconds.
- Restore namespace init: `mv docassemble/__init__.py.bak docassemble/__init__.py` (if needed)

### Code Quality Checks
- `black --check .` -- check formatting (0.5 seconds)
- `black .` -- apply formatting (1-2 seconds)
- Always run `black .` before committing changes or CI will fail.

## Validation

### Limited Environment Validation
When docassemble framework is not available (common in constrained environments):
- ALWAYS run `pip install -e .` to ensure package installs correctly
- ALWAYS run `black --check .` to verify formatting
- ALWAYS run `python setup.py check` to validate package metadata
- Basic import test: `python -c "import docassemble.ALToolbox; print(docassemble.ALToolbox.__version__)"`

### Full Environment Validation
When docassemble framework is available:
- ALWAYS run the complete test suite with `python -m unittest discover docassemble`
- ALWAYS run type checking with mypy
- Test specific functionality by importing and testing individual modules
- Validate YAML templates are syntactically correct

### CRITICAL Network and Installation Notes
- Installing docassemble dependencies often fails due to network timeouts or firewall restrictions
- In constrained environments, focus on package structure validation and code quality checks
- The full docassemble framework is REQUIRED for running unit tests - they will fail without it
- If `pip install -r docassemble/ALToolbox/requirements.txt` fails with timeout, this is EXPECTED in restricted environments

## Common Tasks

### Repository Structure
```
docassemble-ALToolbox/
├── .github/workflows/           # CI/CD workflows
├── docassemble/
│   └── ALToolbox/              # Main package
│       ├── *.py                # Python modules (17 files)
│       ├── data/
│       │   ├── questions/      # YAML templates (41 files)
│       │   ├── static/         # CSS, JS, HTML (6+ files)
│       │   └── templates/      # Jinja2 templates
│       └── test_*.py           # Unit tests (3 files)
├── setup.py                    # Package configuration
├── pyproject.toml              # Tool configuration (Black, mypy)
└── README.md                   # Documentation
```

### Key Python Modules
- `misc.py` -- Core utility functions (thousands, button_array, etc.)
- `business_days.py` -- Business day calculations
- `al_income.py` -- Income-related functions
- `llms.py` -- Large Language Model integration
- `addenda.py` -- Document addenda handling

### Key YAML Files
- `altoolbox_overview.yml` -- Main overview and demo index
- `*_demo.yml` -- Demonstration files for each component
- `*.yml` (non-demo) -- Reusable template components

### Development Workflow
1. Make changes to Python files or YAML templates
2. Run `black .` to format code
3. If full docassemble available: run `python -m unittest discover docassemble`
4. If limited environment: run basic validation commands
5. Test specific functionality by creating small test scripts
6. Always check that package imports correctly with `pip install -e .`

## Known Issues and Limitations

### Environment Constraints
- Tests CANNOT run without full docassemble framework installation
- docassemble installation often fails due to network/firewall restrictions
- In constrained environments, rely on syntax validation and formatting checks
- CI uses GitHub Actions with SuffolkLITLab/ALActions for proper testing environment

### Working Around Constraints
- Use `python -c "exec(open('path/to/file.py').read())"` for basic syntax validation
- Test YAML syntax with `python -c "import yaml; list(yaml.safe_load_all(open('file.yml')))"` (uses safe_load_all for multi-document YAML files)
- Focus on code quality and structure when full testing isn't available
- Create minimal test scripts that don't require docassemble imports

### Timing Expectations
- Package installation: 5-10 seconds (when network is available), FAILS with timeout in restricted environments
- Code formatting check: 0.2-0.5 seconds  
- Code formatting apply: 0.2 seconds
- Package metadata check: 0.15 seconds
- Basic import validation: 0.1 seconds
- Full docassemble installation: 5-15 minutes (if network allows)
- Unit tests: 30-60 seconds (if docassemble available)
- Type checking: 10-30 seconds (if mypy and docassemble available)

## Framework Information

### Docassemble Integration
This package is designed to work with Docassemble, a web application for guided interviews and document assembly. The YAML files define interview questions and logic, while Python modules provide utility functions.

### Testing Philosophy  
- Unit tests validate business logic and utility functions
- Demo YAML files serve as integration tests and usage examples
- Code quality enforced through Black formatting and mypy type checking
- CI/CD through GitHub Actions ensures consistent testing environment

Always validate your changes work correctly within the constraints of your environment, focusing on what can be tested rather than what cannot.