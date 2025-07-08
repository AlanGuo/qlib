"""
Crypto-specific alpha factors based on Alpha158 framework.
Extends qlib's factor system for cryptocurrency trading.
"""

from qlib.data.dataset.loader import QlibDataLoader


class CryptoAlphaDL(QlibDataLoader):
    """
    DataLoader for crypto-specific alpha factors.
    
    Includes decline factors, volume anomaly factors, funding rate factors,
    and momentum factors specifically designed for cryptocurrency markets.
    """

    def __init__(self, config=None, **kwargs):
        _config = {
            "feature": self.get_feature_config(),
        }
        if config is not None:
            _config.update(config)
        super().__init__(config=_config, **kwargs)

    @staticmethod
    def get_feature_config(
        config={
            "basic": {},       # Basic price/volume factors
            "decline": {},     # Decline-specific factors
            "volume": {},      # Volume anomaly factors  
            "momentum": {},    # Momentum factors
            "funding": {},     # Funding rate factors (when available)
        }
    ):
        """
        Create crypto-specific factors from config.
        
        Args:
            config: Configuration dict specifying which factor groups to include
            
        Returns:
            Tuple of (expressions, names) for factor calculation
        """
        expressions = []
        names = []
        
        # Basic price and volume factors (similar to Alpha158)
        if "basic" in config:
            basic_expressions, basic_names = _get_basic_factors()
            expressions.extend(basic_expressions)
            names.extend(basic_names)
        
        # Decline factors - multi-period price decline metrics
        if "decline" in config:
            decline_expressions, decline_names = _get_decline_factors()
            expressions.extend(decline_expressions)
            names.extend(decline_names)
            
        # Volume anomaly factors
        if "volume" in config:
            volume_expressions, volume_names = _get_volume_factors()
            expressions.extend(volume_expressions)
            names.extend(volume_names)
            
        # Momentum factors
        if "momentum" in config:
            momentum_expressions, momentum_names = _get_momentum_factors()
            expressions.extend(momentum_expressions)
            names.extend(momentum_names)
            
        # Funding rate factors (optional - only if data available)
        if "funding" in config:
            funding_expressions, funding_names = _get_funding_factors()
            expressions.extend(funding_expressions)
            names.extend(funding_names)
            
        return expressions, names


def _get_basic_factors():
    """Get basic price and volume factors."""
    expressions = []
    names = []
    
    # Basic K-bar factors (from Alpha158)
    expressions.extend([
        "($close-$open)/$open",
        "($high-$low)/$open", 
        "($close-$open)/($high-$low+1e-12)",
        "($high-Greater($open, $close))/$open",
        "(Less($open, $close)-$low)/$open",
        "(2*$close-$high-$low)/$open",
    ])
    names.extend([
        "KMID", "KLEN", "KMID2", "KUP", "KLOW", "KSFT"
    ])
    
    # Price factors - multiple time periods
    windows = [0, 1, 2, 3, 4, 5, 10, 20, 30]
    for d in windows:
        if d == 0:
            expressions.append("$close/$close")
            names.append("CLOSE0")
        else:
            expressions.append(f"Ref($close, {d})/$close")
            names.append(f"CLOSE{d}")
    
    # Volume factors
    for d in windows:
        if d == 0:
            expressions.append("$volume/($volume+1e-12)")
            names.append("VOLUME0")
        else:
            expressions.append(f"Ref($volume, {d})/($volume+1e-12)")
            names.append(f"VOLUME{d}")
    
    return expressions, names


def _get_decline_factors():
    """Get decline-specific factors for crypto markets."""
    expressions = []
    names = []
    
    # Multi-period decline rates (4H, 8H, 24H, 7D, 14D, 30D in hours)
    periods = [4, 8, 24, 168, 336, 720]
    
    # Cumulative decline over different periods
    for period in periods:
        # Decline rate: (current - past) / past
        expressions.append(f"(Ref($close, {period}) - $close) / Ref($close, {period})")
        names.append(f"DECLINE_{period}H")
    
    # Maximum drawdown over periods
    for period in periods:
        # Max drawdown: (current - period_max) / period_max
        expressions.append(f"($close - Max($close, {period})) / Max($close, {period})")
        names.append(f"MAXDD_{period}H")
    
    # Decline acceleration (short vs long term)
    short_periods = [4, 8, 24]
    long_periods = [168, 336, 720]
    
    for short_p in short_periods:
        for long_p in long_periods:
            if short_p < long_p:
                # Short term decline rate
                short_expr = f"(Ref($close, {short_p}) - $close) / Ref($close, {short_p})"
                # Long term decline rate normalized to short period
                long_expr = f"(Ref($close, {long_p}) - $close) / Ref($close, {long_p}) * {long_p / short_p}"
                # Acceleration ratio
                expressions.append(f"({short_expr}) / ({long_expr} + 1e-8)")
                names.append(f"DECLINE_ACCEL_{short_p}H_VS_{long_p}H")
    
    # Decline volatility
    for period in [24, 168, 336]:
        expressions.append(f"Std(($close - Ref($close, 1)) / Ref($close, 1), {period})")
        names.append(f"DECLINE_VOL_{period}H")
    
    return expressions, names


def _get_volume_factors():
    """Get volume anomaly factors."""
    expressions = []
    names = []
    
    # Volume Z-score (anomaly detection)
    windows = [24, 168, 336]  # 1D, 7D, 14D
    for window in windows:
        expressions.append(f"($volume - Mean($volume, {window})) / Std($volume, {window})")
        names.append(f"VOL_ZSCORE_{window}H")
    
    # Volume ratio (current vs average)
    for window in windows:
        expressions.append(f"$volume / Mean($volume, {window})")
        names.append(f"VOL_RATIO_{window}H")
    
    # Volume-Price divergence indicators
    for window in [24, 168]:
        # Price change vs volume change correlation
        price_change = f"($close - Ref($close, 1)) / Ref($close, 1)"
        volume_change = f"($volume - Ref($volume, 1)) / Ref($volume, 1)"
        expressions.append(f"Corr({price_change}, {volume_change}, {window})")
        names.append(f"PRICE_VOL_CORR_{window}H")
    
    # On-Balance Volume (OBV) related
    for window in [24, 168, 336]:
        # Simplified OBV trend
        expressions.append(f"Mean(Sign($close - Ref($close, 1)) * $volume, {window})")
        names.append(f"OBV_TREND_{window}H")
    
    return expressions, names


def _get_momentum_factors():
    """Get momentum factors for trend analysis."""
    expressions = []
    names = []
    
    # RSI-like factors
    windows = [14, 30, 60]
    for window in windows:
        # Up moves sum
        up_moves = f"Sum(If($close > Ref($close, 1), $close - Ref($close, 1), 0), {window})"
        # Down moves sum  
        down_moves = f"Sum(If($close < Ref($close, 1), Ref($close, 1) - $close, 0), {window})"
        # RSI calculation
        expressions.append(f"100 - 100 / (1 + ({up_moves}) / ({down_moves} + 1e-8))")
        names.append(f"RSI_{window}")
    
    # MACD-like factors
    fast_windows = [12, 24]
    slow_windows = [26, 48]
    for fast, slow in zip(fast_windows, slow_windows):
        # MACD line
        expressions.append(f"Mean($close, {fast}) - Mean($close, {slow})")
        names.append(f"MACD_{fast}_{slow}")
    
    # Bollinger Band position
    for window in [20, 50]:
        # Position within Bollinger Bands
        bb_expr = f"($close - Mean($close, {window})) / (2 * Std($close, {window}) + 1e-8)"
        expressions.append(bb_expr)
        names.append(f"BB_POS_{window}")
    
    # Momentum (Rate of Change)
    periods = [1, 4, 24, 168]
    for period in periods:
        expressions.append(f"($close - Ref($close, {period})) / Ref($close, {period})")
        names.append(f"ROC_{period}H")
    
    return expressions, names


def _get_funding_factors():
    """
    Get funding rate factors (placeholder for when funding rate data is available).
    Note: This assumes funding rate data is stored as $funding_rate field.
    """
    expressions = []
    names = []
    
    # Funding rate Z-score
    windows = [24, 168, 336]
    for window in windows:
        expressions.append(f"($funding_rate - Mean($funding_rate, {window})) / Std($funding_rate, {window})")
        names.append(f"FUNDING_ZSCORE_{window}H")
    
    # Funding rate vs price divergence
    for window in [24, 168]:
        price_change = f"($close - Ref($close, 1)) / Ref($close, 1)"
        funding_change = f"$funding_rate - Ref($funding_rate, 1)"
        expressions.append(f"Corr({price_change}, {funding_change}, {window})")
        names.append(f"FUNDING_PRICE_CORR_{window}H")
    
    return expressions, names


# Convenience class for backward compatibility
class CryptoAlpha158DL(CryptoAlphaDL):
    """Alias for CryptoAlphaDL with default config similar to Alpha158."""
    
    def __init__(self, config=None, **kwargs):
        default_config = {
            "feature": self.get_feature_config({
                "basic": {},
                "decline": {},
                "volume": {},
                "momentum": {},
                # "funding": {},  # Enable when funding data available
            })
        }
        if config is not None:
            default_config.update(config)
        super(CryptoAlphaDL, self).__init__(config=default_config, **kwargs)