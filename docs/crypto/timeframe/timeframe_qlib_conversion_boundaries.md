# Qlib Internal Conversion Function - Usage Boundaries

## Overview

This document defines the strict usage boundaries for the `convert_for_qlib_internal()` function in the cryptocurrency data collector. This function exists solely for compatibility with Qlib's internal storage API and has very specific usage constraints.

## Function Purpose

The `convert_for_qlib_internal()` function performs minimal conversion from our standard timeframe format to Qlib's internal storage API format. Currently, it only converts:
- `1h` → `60min` (Qlib storage API expects minutes for hour intervals)
- All other formats remain unchanged

## Strict Usage Boundaries

### ✅ ALLOWED USAGE

The function should ONLY be used in the following contexts:

1. **storage_manager.py**
   - When creating `FileFeatureStorage` instances
   - When creating `FileInstrumentStorage` instances  
   - When creating `FileCalendarStorage` instances
   - When interfacing with any Qlib storage classes

2. **qlib_data_generator.py**
   - When calling Qlib storage APIs
   - When interfacing with Qlib storage classes

### ❌ FORBIDDEN USAGE

The function should NEVER be used in:

1. **User-facing APIs**
   - timeframe_manager.py
   - Any functions that users call directly
   - Configuration processing

2. **Data collection logic**
   - collector.py
   - exchange_adapters/*
   - Any code that fetches data from exchanges

3. **File system operations**
   - Directory creation/naming
   - File naming
   - Path construction

4. **Configuration processing**
   - Loading configuration files
   - Validating user input
   - Processing timeframe lists

5. **Any code that handles user input**
   - CLI argument processing
   - YAML configuration parsing
   - User-provided timeframe validation

## Rationale

### Why These Boundaries Exist

1. **Separation of Concerns**: The conversion is purely an implementation detail of Qlib's storage layer
2. **Consistency**: All other parts of the system should use standard timeframe formats
3. **Maintainability**: Limiting usage prevents the conversion logic from spreading throughout the codebase
4. **User Experience**: Users should never see or deal with converted formats

### Design Philosophy

- **Minimal Conversion**: Only convert what's absolutely necessary
- **Boundary Isolation**: Keep the conversion contained to storage operations
- **Standard Everywhere**: Use standard formats (`1h`, `1d`) everywhere else

## Examples

### ✅ Correct Usage

```python
# storage_manager.py
from config.timeframes import convert_for_qlib_internal

def save_feature_data(self, data, instrument, field, freq):
    # Convert ONLY when interfacing with Qlib storage API
    qlib_freq = convert_for_qlib_internal(freq)
    
    storage = FileFeatureStorage(
        instrument=instrument,
        field=field,
        freq=qlib_freq,  # Use converted format for Qlib API
        provider_uri=self.provider_uri
    )
    
    # Directory still uses original format
    feature_dir = self.data_dir / freq / "features"
```

```python
# qlib_data_generator.py
from config.timeframes import convert_for_qlib_internal

def create_calendar(self, freq):
    # Convert ONLY for Qlib storage API
    qlib_freq = convert_for_qlib_internal(freq)
    
    storage = FileCalendarStorage(
        freq=qlib_freq,  # Use converted format for Qlib API
        provider_uri=self.provider_uri
    )
    
    # Directory still uses original format
    calendar_dir = self.data_dir / freq / "calendars"
```

### ❌ Incorrect Usage

```python
# timeframe_manager.py - WRONG!
def get_timeframe_info(self, timeframe):
    # DON'T convert in user-facing APIs
    converted = convert_for_qlib_internal(timeframe)  # ❌ WRONG
    return {"timeframe": converted}  # ❌ Users should see standard format
```

```python
# collector.py - WRONG!
def collect_data(self, timeframes):
    for tf in timeframes:
        # DON'T convert in data collection logic
        converted_tf = convert_for_qlib_internal(tf)  # ❌ WRONG
        exchange_tf = get_exchange_timeframe(exchange, converted_tf)  # ❌ WRONG
```

```python
# File naming - WRONG!
def create_file_path(self, timeframe, field):
    # DON'T convert for file naming
    converted = convert_for_qlib_internal(timeframe)  # ❌ WRONG
    return f"{field}.{converted}.bin"  # ❌ Should use original format
```

## Boundary Violation Detection

The function includes built-in boundary checking:

```python
def convert_for_qlib_internal(timeframe: str) -> str:
    # Validates timeframe first
    if not validate_timeframe(timeframe):
        raise ValueError(f"Invalid timeframe '{timeframe}' - boundary violation")
    
    # Issues warnings for inappropriate usage
    _validate_qlib_internal_usage()
    
    # Only converts what's necessary
    if timeframe == "1h":
        return "60min"
    return timeframe
```

## Migration Guidelines

If you find existing code that violates these boundaries:

### 1. Identify the Violation
- Look for calls to `convert_for_qlib_internal()` outside allowed modules
- Check if the conversion is used for non-storage purposes

### 2. Fix the Violation
- Remove the conversion call if it's not needed
- Use the original timeframe format instead
- Only keep the conversion if interfacing with Qlib storage APIs

### 3. Example Migration

```python
# Before (violation)
def create_directory(self, timeframe):
    converted = convert_for_qlib_internal(timeframe)  # ❌ WRONG
    dir_path = self.base_dir / converted
    dir_path.mkdir(exist_ok=True)

# After (correct)
def create_directory(self, timeframe):
    # Use original format for directory naming
    dir_path = self.base_dir / timeframe  # ✅ CORRECT
    dir_path.mkdir(exist_ok=True)
```

## Testing Boundaries

Always test both the function and its boundaries:

```python
def test_convert_for_qlib_internal_boundaries():
    """Test that the function is used correctly."""
    
    # Test the conversion works
    assert convert_for_qlib_internal("1h") == "60min"
    assert convert_for_qlib_internal("1d") == "1d"
    
    # Test boundary validation
    with pytest.raises(ValueError):
        convert_for_qlib_internal("invalid")
    
    # Test usage from wrong context triggers warning
    with pytest.warns(UserWarning):
        # This should trigger a boundary violation warning
        convert_for_qlib_internal("1h")
```

## Common Mistakes to Avoid

1. **Using conversion in user-facing APIs**: Users should never see converted formats
2. **Converting for file system operations**: Use original formats for directories and files
3. **Converting in data collection**: Exchange adapters should use original formats
4. **Converting in configuration processing**: Config files should use standard formats
5. **Over-converting**: Only convert when absolutely necessary for Qlib storage API

## Summary

The `convert_for_qlib_internal()` function has a very specific and limited purpose:
- **ONLY** use it when interfacing with Qlib storage classes
- **NEVER** use it for user-facing operations, file naming, or data collection
- **ALWAYS** use original timeframe formats everywhere else

This boundary ensures that the conversion remains an isolated implementation detail and doesn't leak into other parts of the system, maintaining consistency and user experience.