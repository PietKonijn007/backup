---
inclusion: always
---

# Utility File Organization Guidelines

## Directory Structure

This project maintains a clean separation between core application files and utility/documentation files:

### Core Application Files (Root Directory)
- `app.py` - Main Flask application
- `config.yaml` - Application configuration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables
- Core directories: `src/`, `templates/`, `static/`, `tests/`, `docs/`

### Utility Scripts (`util-scripts/`)
Store standalone Python scripts that are used for:
- Testing and diagnostics (e.g., `test_*.py`)
- One-time fixes and maintenance (e.g., `fix_*.py`)
- Setup and initialization utilities (e.g., `init_*.py`)
- Diagnostic and verification tools (e.g., `diagnose_*.py`, `verify_*.py`)
- Cost optimization and monitoring tools

### Utility Documentation (`util-docs/`)
Store markdown files that are:
- Implementation notes and technical details
- Bug reports and troubleshooting guides
- Deployment guides for specific scenarios
- Feature implementation documentation
- Historical documentation and summaries

## File Naming Conventions

### Python Utility Scripts
- `test_*.py` - Testing and validation scripts
- `fix_*.py` - Problem resolution scripts
- `init_*.py` - Initialization and setup scripts
- `diagnose_*.py` - Diagnostic tools
- `verify_*.py` - Verification utilities
- `*_tools.py` - Utility toolsets

### Markdown Documentation
- `*_IMPLEMENTATION.md` - Feature implementation details
- `*_GUIDE.md` - Step-by-step guides
- `*_BUG_REPORT.md` - Bug documentation
- `*_SUMMARY.md` - Summary documents
- `*_COMMANDS.md` - Command references

## When Creating New Files

### Always place in `util-scripts/` if:
- The file is a standalone Python script
- It's used for testing, debugging, or maintenance
- It's not part of the core application runtime
- It's a one-time use or diagnostic tool

### Always place in `util-docs/` if:
- The file is documentation about implementation details
- It's a troubleshooting or deployment guide
- It's historical documentation or bug reports
- It's not part of the main user-facing documentation

### Keep in root directory only if:
- It's essential for application runtime (`app.py`, `config.yaml`)
- It's core project documentation (`README.md`)
- It's configuration files (`.env`, `requirements.txt`)
- It's deployment scripts used in production (`deploy.sh`)

## Examples of Proper Organization

✅ **Correctly Organized:**
```
util-scripts/
├── test_oauth_credentials.py
├── fix_expired_token.py
├── diagnose_photos_scope.py
└── cost_optimization_tools.py

util-docs/
├── GOOGLE_PHOTOS_BUG_REPORT.md
├── TOKEN_FIX_SUMMARY.md
└── DEPLOYMENT_QUICK_START.md
```

❌ **Avoid in Root:**
```
root/
├── test_something.py          # Should be in util-scripts/
├── IMPLEMENTATION_NOTES.md    # Should be in util-docs/
└── debug_tool.py             # Should be in util-scripts/
```

## Maintenance

Regularly review the root directory and move any utility files that accumulate there to the appropriate utility directories to maintain a clean project structure.