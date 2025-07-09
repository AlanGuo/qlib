# OKX Timeframe Format Warning

## ⚠️ CRITICAL WARNING

**OKX timeframes are LOWERCASE, NOT uppercase!**

This is one of the most common sources of bugs and confusion when working with OKX integration.

## The Problem

Many developers assume OKX follows a "standard" uppercase format for timeframes, but this is **INCORRECT**.

### ❌ WRONG (Common Mistake)
```python
# These will cause "Timeframe not supported" errors
"1H"  # Incorrect - uppercase
"1D"  # Incorrect - uppercase  
"1W"  # Incorrect - uppercase
```

### ✅ CORRECT
```python
# These are the actual OKX timeframe formats
"1h"  # Correct - lowercase
"1d"  # Correct - lowercase
"1w"  # Correct - lowercase
```

## Why This Happens

1. **Documentation inconsistency**: Some unofficial docs show uppercase
2. **Other exchanges**: Some exchanges do use uppercase, creating confusion
3. **"Looks more standard"**: Uppercase "looks" more professional/standard
4. **Case sensitivity**: Easy to overlook in code reviews

## Evidence

This has been verified through:
- ✅ Direct testing with OKX API
- ✅ CCXT library timeframe validation
- ✅ OKX official API documentation
- ✅ Production environment testing

## Current Implementation

In our codebase, this is handled correctly in:

```python
# config/timeframes.py
EXCHANGE_TIMEFRAME_MAPPING = {
    "okx": {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m", 
        "30min": "30m",
        "1h": "1h",     # ✅ CORRECT - lowercase
        "1d": "1d",     # ✅ CORRECT - lowercase
        "1w": "1w",     # ✅ CORRECT - lowercase
    },
}
```

## Error Symptoms

If you accidentally use uppercase timeframes, you'll see errors like:
```
Timeframe 1H not supported by OKX. Supported: ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M', '3M']
```

Notice that the supported list shows `1h`, `1d`, `1w` (lowercase).

## Developer Guidelines

### When Reviewing Code
- ❌ Do NOT "fix" lowercase to uppercase - it's correct as-is
- ❌ Do NOT assume uppercase is more "standard"
- ✅ Double-check any timeframe changes against this documentation

### When Adding New Timeframes
- Always use lowercase for hour, day, week intervals
- Test against actual OKX API before committing
- Add unit tests to verify timeframe conversion

### When Debugging
- First check: are you using correct case?
- Compare against the supported timeframes list from OKX
- Remember: case sensitivity matters!

## Historical Context

This issue has caused multiple bugs in the past:
- 2024-12: Initial implementation incorrectly used uppercase
- 2024-12: Fixed after test failures revealed the issue
- 2025-01: Added comprehensive warnings to prevent regression

## Quick Reference

| Standard | OKX Format | Status |
|----------|------------|--------|
| 1min     | 1m         | ✅ Works |
| 5min     | 5m         | ✅ Works |
| 15min    | 15m        | ✅ Works |
| 30min    | 30m        | ✅ Works |
| 1h       | 1h         | ✅ Works (lowercase!) |
| 1d       | 1d         | ✅ Works (lowercase!) |
| 1w       | 1w         | ✅ Works (lowercase!) |

## Related Files

Files that contain OKX timeframe handling:
- `config/timeframes.py` - Main timeframe mapping
- `exchange_adapters/okx_adapter.py` - OKX adapter implementation
- `tests/test_exchange_connection.py` - Integration tests

## Remember

**When in doubt, use lowercase for OKX timeframes!**

This documentation exists because this mistake happens repeatedly. Please help prevent future bugs by spreading awareness of this issue.