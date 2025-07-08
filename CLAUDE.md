# claude.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Qlib is Microsoft's AI-oriented quantitative investment platform, supporting the full ML pipeline for quantitative investment. It's written in Python (3.8-3.12) with modular architecture and loose-coupled components.

## Architecture Overview

The codebase follows a layered architecture with these key components:

- **Data Layer** (`qlib/data/`): Core data infrastructure with caching, storage backends, and data operations
- **Model Layer** (`qlib/model/`): ML model implementations including ensemble and meta-learning capabilities
- **Backtest Engine** (`qlib/backtest/`): Portfolio simulation and performance evaluation systems
- **Workflow Management** (`qlib/workflow/`): Experiment management with CLI interface (`qrun`)
- **Contributed Models** (`qlib/contrib/`): 20+ state-of-the-art quantitative models

## Development Commands

### Setup and Installation
```bash
# Install in development mode
pip install -e .

# Install with all extras
pip install -e .[dev]

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=qlib

# Run slow tests (marked with @pytest.mark.slow)
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

### Code Quality
```bash
# Format code with black (120 char line length)
black qlib/ --line-length 120

# Run linting
pylint qlib/
flake8 qlib/
mypy qlib/

# Format notebooks
nbqa black scripts/ --line-length 120
```

### Build System
```bash
# Build package
python setup.py build_ext --inplace

# Clean build artifacts
make clean

# Full development setup
make install
```

### Data Collection
```bash
# Crypto data collector (most comprehensive)
cd scripts/data_collector/crypto
python -m crypto_collector --help

# Yahoo data collector
cd scripts/data_collector/yahoo
python collector.py --help
```

### Running Experiments
```bash
# Run workflow with qrun
qrun configs/workflow_config_lightgbm_Alpha158.yaml

# Custom experiment
python -m qlib.workflow.cli --config_path your_config.yaml
```

## Key Development Patterns

### Data Format
- Uses optimized binary storage (.bin files) for efficient quantitative data access
- Data operations through `qlib.data.D` interface
- Caching mechanisms for performance optimization

### Model Development
- Models inherit from `qlib.model.base.Model`
- Support for both classical ML (LightGBM, XGBoost) and deep learning models
- Ensemble and meta-learning frameworks available

### Configuration Management
- YAML-based configuration system
- Hierarchical config structure with inheritance
- Runtime configuration via `qlib.config.C`

### Testing Strategy
- Comprehensive test coverage with pytest
- Slow tests separated with `@pytest.mark.slow` decorator
- Mock data and fixtures for unit testing
- Integration tests for end-to-end workflows

## Crypto Data Collector Architecture

The crypto data collector is the most sophisticated component with:

- **Multi-exchange support**: Via CCXT library
- **Incremental updates**: Production-ready incremental data collection
- **Validation framework**: Data quality checks and risk metrics
- **CLI interface**: Full command-line tool with configuration templates
- **Storage management**: Efficient data storage and retrieval

Located in `scripts/data_collector/crypto/` with comprehensive documentation and examples.

## Important File Locations

- Main package: `qlib/`
- Configuration files: `qlib/config/`
- Data providers: `qlib/data/provider/`
- Model implementations: `qlib/model/` and `qlib/contrib/`
- Workflow configs: `examples/benchmarks/`
- Documentation: `docs/`

## CI/CD and Quality Assurance

- GitHub Actions workflow supporting Linux, Windows, macOS
- Python 3.8-3.12 compatibility testing
- Pre-commit hooks available
- Automated package publishing
- Comprehensive linting with Black, Pylint, Flake8, MyPy

## Common Development Tasks

### Adding New Models
1. Implement in `qlib/contrib/model/`
2. Follow existing model patterns
3. Add comprehensive tests
4. Update documentation

### Data Provider Development
1. Implement in `qlib/data/provider/`
2. Follow provider interface patterns
3. Add data validation
4. Include performance tests

### Workflow Configuration
1. Create YAML config following existing patterns
2. Test with `qrun` command
3. Validate results and performance metrics