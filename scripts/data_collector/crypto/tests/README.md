# Crypto Data Collector Tests

## Quick Start

```bash
# Run all tests
python run_all_tests.py

# Run specific test categories
pytest unit/ -v                    # Unit tests
pytest integration/ -v             # Integration tests
pytest live/ -v                    # Live API tests (requires network)
pytest performance/ -v             # Performance tests

# Run without live tests (for offline development)
python run_all_tests.py --no-live
```

## Test Structure

```
tests/
├── unit/                    # Unit tests (fast, no network required)
├── integration/             # Integration tests
├── live/                   # Live API tests (requires network)
├── performance/            # Performance tests
├── runners/                # Specialized test runners
│   └── run_comprehensive_live_test.py
├── config/                 # Test configuration
└── run_all_tests.py        # Main test runner
```

## Test Reports

Test reports are automatically saved to the `reports/` directory:

- **Live test reports**: `test_report_live_YYYYMMDD_HHMMSS.json`
- **General test reports**: `test_report_YYYYMMDD_HHMMSS.txt`
- **Coverage reports**: `htmlcov/` (if coverage is enabled)

### Managing Reports

```bash
# List all reports
python manage_reports.py list

# Show summary
python manage_reports.py summary

# Clean old reports (older than 30 days)
python manage_reports.py clean --days 30
```

## Configuration

For live tests, you may need to configure network proxy:

```bash
export https_proxy=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808
```

## Documentation

- `new_user_quickstart.md` - Detailed quick start guide
- `docs/testing_guide.md` - Complete testing documentation