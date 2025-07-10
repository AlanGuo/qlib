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

## Configuration

For live tests, you may need to configure network proxy:

```bash
export https_proxy=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808
```

## Documentation

- `new_user_quickstart.md` - Detailed quick start guide
- `docs/testing_guide.md` - Complete testing documentation