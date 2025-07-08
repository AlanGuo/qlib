#!/usr/bin/env python3
"""
BTC Dominance Strategy (BtcDom2) for Qlib

This module implements a comprehensive cryptocurrency strategy based on BTC dominance analysis that:
1. Uses 171 crypto-specific factors for multi-factor ranking
2. Dynamically screens altcoins for shorting based on factor scores
3. Manages capital allocation between BTC spot and short pool
4. Implements dynamic rebalancing and liquidity filtering

Author: CryptoAlpha Development Team
License: MIT
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
import logging
from datetime import datetime, timedelta

from qlib.strategy.base import BaseStrategy
from qlib.backtest.decision import BaseTradeDecision, Order, TradeDecisionWO
from qlib.data.data import D
from qlib.contrib.data.crypto_loader import CryptoFactorDL
from qlib.contrib.data.crypto_factors import CryptoFactorLibrary, FactorConfig, FactorCategory
from qlib.utils import lazy_sort_index


class WeightingScheme(Enum):
    """Enumeration of available weighting schemes."""
    EQUAL_WEIGHT = "equal_weight"
    FACTOR_WEIGHTED = "factor_weighted"  
    RISK_PARITY = "risk_parity"
    VOLATILITY_WEIGHTED = "volatility_weighted"


class RebalanceFrequency(Enum):
    """Enumeration of rebalancing frequencies."""
    HOURLY_4 = "4h"
    HOURLY_8 = "8h"
    HOURLY_12 = "12h"
    DAILY = "1d"


@dataclass
class BtcDom2Config:
    """Configuration for BTC Dominance strategy."""
    
    # Core strategy parameters
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.HOURLY_8
    factor_lookback_days: int = 14  # m: factor calculation period
    num_short_positions: int = 10   # x: number of altcoins to short
    
    # Capital allocation
    btc_spot_ratio: float = 0.5  # BTC spot allocation (30%-70%)
    short_pool_ratio: float = 0.5  # Short pool allocation
    
    # Weighting and selection
    weighting_scheme: WeightingScheme = WeightingScheme.FACTOR_WEIGHTED
    factor_categories: List[FactorCategory] = field(default_factory=lambda: [
        FactorCategory.DECLINE, FactorCategory.VOLUME, 
        FactorCategory.MOMENTUM, FactorCategory.FUNDING
    ])
    
    # Liquidity filtering (based on available data)
    min_daily_volume: float = 1e6  # Minimum daily volume in USD
    max_spread_estimate: float = 2.0  # Maximum estimated spread % (high-low based)
    min_trade_activity: float = 0.1  # Minimum relative trading activity
    
    # Dynamic parameters
    enable_dynamic_sizing: bool = True
    volatility_lookback: int = 30  # days for volatility calculation
    max_position_size: float = 0.15  # Maximum single position size
    
    # Factor scoring
    factor_weights: Dict[str, float] = field(default_factory=lambda: {
        "decline": 0.3,   # Higher weight for decline factors
        "volume": 0.25,   # Volume anomaly detection
        "momentum": 0.25, # Momentum reversal signals
        "funding": 0.2    # Funding rate distortions
    })
    
    # Risk management (enhanced)
    stop_loss_threshold: float = 0.15  # 15% stop loss per position
    portfolio_stop_loss: float = 0.10   # 10% portfolio-level stop loss
    max_drawdown_threshold: float = 0.20  # 20% max drawdown threshold
    position_concentration_limit: float = 0.25  # Max 25% in single position
    correlation_limit: float = 0.7  # Max correlation between positions
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.3 <= self.btc_spot_ratio <= 0.7:
            raise ValueError("BTC spot ratio must be between 30% and 70%")
        
        if not 5 <= self.num_short_positions <= 20:
            raise ValueError("Number of short positions must be between 5 and 20")
        
        if abs(self.btc_spot_ratio + self.short_pool_ratio - 1.0) > 1e-6:
            raise ValueError("BTC spot ratio and short pool ratio must sum to 1.0")


class BtcDom2Strategy(BaseStrategy):
    """
    Advanced BTC Dominance strategy with multi-factor ranking.
    
    This strategy implements a sophisticated approach to cryptocurrency trading based on BTC dominance:
    
    1. **Multi-Factor Screening**: Uses 171 crypto-specific factors across 5 categories
       to identify weak altcoins suitable for shorting
    
    2. **Dynamic Capital Allocation**: Manages capital between BTC spot holdings 
       (defensive position) and short pool (aggressive positions)
    
    3. **Liquidity Filtering**: Ensures adequate liquidity for entry/exit
    
    4. **Risk Management**: Implements position sizing, concentration limits, and 
       dynamic rebalancing
    
    Key Features:
    - Factor-based altcoin screening using decline, volume, momentum, and funding factors
    - Multiple weighting schemes (equal weight, factor weighted, risk parity)
    - Adaptive position sizing based on volatility and factor strength
    - 24/7 crypto market support with configurable rebalancing frequencies
    """
    
    def __init__(self, config: Optional[BtcDom2Config] = None, **kwargs):
        """
        Initialize the BTC Dominance strategy.
        
        Parameters
        ----------
        config : BtcDom2Config, optional
            Strategy configuration. If None, uses default configuration.
        **kwargs
            Additional arguments passed to BaseStrategy
        """
        super().__init__(**kwargs)
        
        self.config = config or BtcDom2Config()
        
        # Initialize factor computation
        factor_config = FactorConfig(
            categories=self.config.factor_categories,
            market_type="perpetual",  # Use perpetual for funding factors
            normalization="zscore"
        )
        self.factor_library = CryptoFactorLibrary(factor_config)
        self.factor_loader = CryptoFactorDL(
            timeframe="1h", 
            market_type="perpetual"
        )
        
        # Strategy state
        self.current_positions = {}
        self.last_rebalance_time = None
        self.factor_scores_cache = {}
        self.liquidity_metrics_cache = {}
        
        # Risk management state
        self.position_entry_prices = {}  # Track entry prices for stop loss
        self.portfolio_peak_value = 0.0  # Track peak for drawdown calculation
        self.risk_alerts = []  # Track risk alerts
        
        # Performance tracking
        self.rebalance_count = 0
        self.position_history = []
        
    def generate_trade_decision(self, execute_result=None):
        """
        Generate trade decisions based on multi-factor analysis.
        
        This is the main strategy logic that:
        1. Computes factor scores for all eligible cryptocurrencies
        2. Filters by liquidity requirements
        3. Ranks and selects top candidates for shorting
        4. Determines position sizes and generates orders
        
        Returns
        -------
        BaseTradeDecision
            Trade decision containing orders for the current rebalancing period
        """
        current_time = self.trade_calendar.get_current_time()
        
        # Check if rebalancing is needed
        if not self._should_rebalance(current_time):
            return TradeDecisionWO([], self)
        
        try:
            # Step 0: Risk management checks
            risk_orders = self._check_risk_management(current_time)
            if risk_orders:
                # Emergency risk management orders take priority
                self.logger.warning(f"Risk management triggered: {len(risk_orders)} emergency orders")
                return TradeDecisionWO(risk_orders, self)
            
            # Step 1: Get universe of tradeable cryptocurrencies
            universe = self._get_tradeable_universe(current_time)
            
            if len(universe) < self.config.num_short_positions:
                warnings.warn(f"Insufficient tradeable assets: {len(universe)} < {self.config.num_short_positions}")
                return TradeDecisionWO([], self)
            
            # Step 2: Compute factor scores for all assets
            factor_scores = self._compute_factor_scores(universe, current_time)
            
            # Step 3: Apply liquidity filtering
            liquid_assets = self._apply_liquidity_filter(universe, current_time)
            
            # Step 4: Rank assets and select short candidates
            short_candidates = self._select_short_candidates(
                factor_scores, liquid_assets, current_time
            )
            
            # Step 5: Determine position sizes
            position_sizes = self._calculate_position_sizes(
                short_candidates, factor_scores, current_time
            )
            
            # Step 6: Generate orders
            orders = self._generate_orders(position_sizes, current_time)
            
            # Update strategy state
            self.last_rebalance_time = current_time
            self.rebalance_count += 1
            self._update_position_history(short_candidates, position_sizes, current_time)
            
            return TradeDecisionWO(orders, self)
            
        except Exception as e:
            warnings.warn(f"Error in trade decision generation: {e}")
            return TradeDecisionWO([], self)
    
    def _should_rebalance(self, current_time: pd.Timestamp) -> bool:
        """
        Enhanced rebalancing logic with multiple trigger conditions.
        
        Rebalancing occurs when ANY of these conditions are met:
        1. Time-based: Regular frequency schedule
        2. Performance-based: Significant position changes
        3. Risk-based: Risk metric threshold breaches
        4. Market-based: Significant market condition changes
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        bool
            True if rebalancing should occur
        """
        # 1. Time-based rebalancing (always check this first)
        if self.last_rebalance_time is None:
            return True
        
        time_diff = current_time - self.last_rebalance_time
        freq_map = {
            RebalanceFrequency.HOURLY_4: timedelta(hours=4),
            RebalanceFrequency.HOURLY_8: timedelta(hours=8),
            RebalanceFrequency.HOURLY_12: timedelta(hours=12),
            RebalanceFrequency.DAILY: timedelta(days=1)
        }
        
        time_based_rebalance = time_diff >= freq_map[self.config.rebalance_frequency]
        
        # If time-based condition is met, always rebalance
        if time_based_rebalance:
            self.logger.info(f"Time-based rebalance triggered: {time_diff} >= {freq_map[self.config.rebalance_frequency]}")
            return True
        
        # 2. Check other conditions only if we have sufficient time elapsed (min 1 hour)
        if time_diff < timedelta(hours=1):
            return False
        
        # 3. Performance-based rebalancing
        if self._check_performance_triggers(current_time):
            self.logger.info("Performance-based rebalance triggered")
            return True
        
        # 4. Risk-based rebalancing
        if self._check_risk_triggers(current_time):
            self.logger.info("Risk-based rebalance triggered")
            return True
        
        # 5. Market condition-based rebalancing
        if self._check_market_triggers(current_time):
            self.logger.info("Market condition-based rebalance triggered")
            return True
        
        return False
    
    def _check_performance_triggers(self, current_time: pd.Timestamp) -> bool:
        """
        Check if performance-based rebalancing triggers are met.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        bool
            True if performance triggers are met
        """
        if not self.position_history or len(self.position_history) < 2:
            return False
        
        try:
            # Get recent position history
            recent_positions = self.position_history[-2:]  # Last 2 rebalances
            current_positions = recent_positions[-1]['short_candidates']
            previous_positions = recent_positions[-2]['short_candidates']
            
            # Calculate position turnover
            common_positions = set(current_positions) & set(previous_positions)
            turnover_rate = 1.0 - (len(common_positions) / max(len(current_positions), 1))
            
            # Trigger if turnover is very high (>70%)
            if turnover_rate > 0.7:
                return True
            
            # Check for significant individual position changes
            current_sizes = recent_positions[-1]['position_sizes']
            previous_sizes = recent_positions[-2]['position_sizes']
            
            for asset in common_positions:
                size_change = abs(current_sizes.get(asset, 0) - previous_sizes.get(asset, 0))
                if size_change > 0.1:  # 10% position size change
                    return True
            
        except Exception as e:
            self.logger.warning(f"Error checking performance triggers: {e}")
        
        return False
    
    def _check_risk_triggers(self, current_time: pd.Timestamp) -> bool:
        """
        Check if risk-based rebalancing triggers are met.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        bool
            True if risk triggers are met
        """
        try:
            # Check BTC volatility (affects hedge ratio)
            btc_data = D.features(
                instruments=["BTC"],
                fields=["$close"],
                start_time=current_time - timedelta(days=7),
                end_time=current_time
            )
            
            if not btc_data.empty and len(btc_data) > 24:
                btc_returns = btc_data["$close"].pct_change().dropna()
                current_vol = btc_returns.tail(24).std() * np.sqrt(24)  # 24h vol
                
                # Trigger if BTC volatility exceeds threshold (>5% daily)
                if current_vol > 0.05:
                    return True
            
            # Check market-wide volatility increase
            if self.position_history:
                last_positions = self.position_history[-1]['short_candidates']
                high_vol_count = 0
                
                for asset in last_positions[:5]:  # Check top 5 positions
                    try:
                        asset_data = D.features(
                            instruments=[asset],
                            fields=["$close"],
                            start_time=current_time - timedelta(days=2),
                            end_time=current_time
                        )
                        
                        if not asset_data.empty and len(asset_data) > 12:
                            returns = asset_data["$close"].pct_change().dropna()
                            recent_vol = returns.tail(12).std() * np.sqrt(24)
                            
                            if recent_vol > 0.1:  # 10% daily volatility
                                high_vol_count += 1
                    except:
                        continue
                
                # Trigger if >60% of positions have high volatility
                if high_vol_count / max(len(last_positions[:5]), 1) > 0.6:
                    return True
            
        except Exception as e:
            self.logger.warning(f"Error checking risk triggers: {e}")
        
        return False
    
    def _check_market_triggers(self, current_time: pd.Timestamp) -> bool:
        """
        Check if market condition-based rebalancing triggers are met.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        bool
            True if market triggers are met
        """
        try:
            # Check for significant BTC price movement (affects strategy dynamics)
            btc_data = D.features(
                instruments=["BTC"],
                fields=["$close"],
                start_time=current_time - timedelta(hours=4),
                end_time=current_time
            )
            
            if not btc_data.empty and len(btc_data) > 2:
                price_change = (btc_data["$close"].iloc[-1] / btc_data["$close"].iloc[0]) - 1
                
                # Trigger if BTC moves >5% in 4 hours
                if abs(price_change) > 0.05:
                    return True
            
            # Check funding rate changes (for perpetual futures)
            # This would be implemented if funding rate data is available
            # For now, we skip this check
            
        except Exception as e:
            self.logger.warning(f"Error checking market triggers: {e}")
        
        return False
    
    def _check_risk_management(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Comprehensive risk management system with multiple safety mechanisms.
        
        Checks for and handles:
        1. Individual position stop losses
        2. Portfolio-level stop losses
        3. Maximum drawdown breaches
        4. Position correlation limits
        5. Emergency market conditions
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Emergency orders for risk management (empty if no action needed)
        """
        emergency_orders = []
        
        try:
            # 1. Check individual position stop losses
            stop_loss_orders = self._check_position_stop_losses(current_time)
            emergency_orders.extend(stop_loss_orders)
            
            # 2. Check portfolio-level risk metrics
            portfolio_orders = self._check_portfolio_risk(current_time)
            emergency_orders.extend(portfolio_orders)
            
            # 3. Check maximum drawdown
            drawdown_orders = self._check_drawdown_limits(current_time)
            emergency_orders.extend(drawdown_orders)
            
            # 4. Check position correlation limits
            correlation_orders = self._check_correlation_limits(current_time)
            emergency_orders.extend(correlation_orders)
            
            # 5. Check for emergency market conditions
            market_orders = self._check_emergency_market_conditions(current_time)
            emergency_orders.extend(market_orders)
            
        except Exception as e:
            self.logger.error(f"Error in risk management system: {e}")
        
        return emergency_orders
    
    def _check_position_stop_losses(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Check individual position stop losses and generate close orders.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Stop loss orders
        """
        stop_loss_orders = []
        
        for asset, entry_price in self.position_entry_prices.items():
            try:
                # Get current price
                price_data = D.features(
                    instruments=[asset],
                    fields=["$close"],
                    start_time=current_time,
                    end_time=current_time
                )
                
                if price_data.empty:
                    continue
                
                current_price = price_data["$close"].iloc[-1]
                
                # Calculate P&L for short position (we profit when price goes down)
                pnl_pct = (entry_price - current_price) / entry_price
                
                # Trigger stop loss if loss exceeds threshold
                if pnl_pct < -self.config.stop_loss_threshold:
                    # Close position (buy to cover short)
                    current_position_size = self.current_positions.get(asset, 0)
                    if current_position_size < 0:  # We have a short position
                        close_order = Order(
                            stock_id=asset,
                            amount=-current_position_size,  # Buy to cover
                            start_time=current_time,
                            end_time=current_time,
                            factor=current_price
                        )
                        stop_loss_orders.append(close_order)
                        
                        # Remove from tracking
                        del self.position_entry_prices[asset]
                        
                        self.logger.warning(f"Stop loss triggered for {asset}: P&L={pnl_pct:.2%}, "
                                          f"Entry=${entry_price:.4f}, Current=${current_price:.4f}")
                        
                        # Add to risk alerts
                        self.risk_alerts.append({
                            'timestamp': current_time,
                            'type': 'stop_loss',
                            'asset': asset,
                            'pnl_pct': pnl_pct,
                            'entry_price': entry_price,
                            'exit_price': current_price
                        })
                
            except Exception as e:
                self.logger.warning(f"Error checking stop loss for {asset}: {e}")
                continue
        
        return stop_loss_orders
    
    def _check_portfolio_risk(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Check portfolio-level risk metrics and generate protective orders.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Portfolio protection orders
        """
        portfolio_orders = []
        
        try:
            # Calculate current portfolio value and P&L
            portfolio_value = self._get_portfolio_value()
            portfolio_pnl = self._calculate_portfolio_pnl(current_time)
            
            # Update peak value tracking
            if portfolio_value > self.portfolio_peak_value:
                self.portfolio_peak_value = portfolio_value
            
            # Check portfolio-level stop loss
            if portfolio_pnl < -self.config.portfolio_stop_loss:
                self.logger.critical(f"Portfolio stop loss triggered: P&L={portfolio_pnl:.2%}")
                
                # Close all positions
                for asset in list(self.current_positions.keys()):
                    if self.current_positions[asset] < 0:  # Short position
                        close_order = Order(
                            stock_id=asset,
                            amount=-self.current_positions[asset],
                            start_time=current_time,
                            end_time=current_time,
                            factor=0  # Market order for emergency exit
                        )
                        portfolio_orders.append(close_order)
                
                # Add to risk alerts
                self.risk_alerts.append({
                    'timestamp': current_time,
                    'type': 'portfolio_stop_loss',
                    'portfolio_pnl': portfolio_pnl,
                    'portfolio_value': portfolio_value
                })
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk: {e}")
        
        return portfolio_orders
    
    def _check_drawdown_limits(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Check maximum drawdown limits and generate protective orders.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Drawdown protection orders
        """
        drawdown_orders = []
        
        try:
            portfolio_value = self._get_portfolio_value()
            
            if self.portfolio_peak_value > 0:
                current_drawdown = (self.portfolio_peak_value - portfolio_value) / self.portfolio_peak_value
                
                if current_drawdown > self.config.max_drawdown_threshold:
                    self.logger.critical(f"Maximum drawdown exceeded: {current_drawdown:.2%}")
                    
                    # Reduce position sizes by 50% to limit further losses
                    for asset, position_size in self.current_positions.items():
                        if position_size < 0:  # Short position
                            reduce_order = Order(
                                stock_id=asset,
                                amount=-position_size * 0.5,  # Close 50% of position
                                start_time=current_time,
                                end_time=current_time,
                                factor=0  # Market order
                            )
                            drawdown_orders.append(reduce_order)
                    
                    # Add to risk alerts
                    self.risk_alerts.append({
                        'timestamp': current_time,
                        'type': 'max_drawdown',
                        'drawdown': current_drawdown,
                        'peak_value': self.portfolio_peak_value,
                        'current_value': portfolio_value
                    })
            
        except Exception as e:
            self.logger.error(f"Error checking drawdown limits: {e}")
        
        return drawdown_orders
    
    def _check_correlation_limits(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Check position correlation limits (placeholder - simplified implementation).
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Correlation-based adjustment orders
        """
        # This would require correlation matrix calculation
        # For now, return empty list as correlation checking is complex
        # and would need significant additional data processing
        return []
    
    def _check_emergency_market_conditions(self, current_time: pd.Timestamp) -> List[Order]:
        """
        Check for emergency market conditions requiring immediate action.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            Emergency market condition orders
        """
        emergency_orders = []
        
        try:
            # Check for extreme BTC volatility (affects entire crypto market)
            btc_data = D.features(
                instruments=["BTC"],
                fields=["$close", "$high", "$low"],
                start_time=current_time - timedelta(hours=2),
                end_time=current_time
            )
            
            if not btc_data.empty and len(btc_data) > 1:
                # Check for extreme price movements
                price_range = (btc_data["$high"].max() - btc_data["$low"].min()) / btc_data["$close"].iloc[-1]
                
                if price_range > 0.15:  # 15% range in 2 hours
                    self.logger.warning(f"Extreme market volatility detected: {price_range:.2%}")
                    
                    # Reduce position sizes by 30%
                    for asset, position_size in self.current_positions.items():
                        if position_size < 0:  # Short position
                            reduce_order = Order(
                                stock_id=asset,
                                amount=-position_size * 0.3,
                                start_time=current_time,
                                end_time=current_time,
                                factor=0
                            )
                            emergency_orders.append(reduce_order)
                    
                    # Add to risk alerts
                    self.risk_alerts.append({
                        'timestamp': current_time,
                        'type': 'extreme_volatility',
                        'btc_price_range': price_range
                    })
            
        except Exception as e:
            self.logger.warning(f"Error checking emergency market conditions: {e}")
        
        return emergency_orders
    
    def _calculate_portfolio_pnl(self, current_time: pd.Timestamp) -> float:
        """
        Calculate current portfolio P&L percentage.
        
        Parameters
        ----------
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        float
            Portfolio P&L as percentage
        """
        try:
            total_pnl = 0.0
            portfolio_value = self._get_portfolio_value()
            
            for asset, entry_price in self.position_entry_prices.items():
                # Get current price
                price_data = D.features(
                    instruments=[asset],
                    fields=["$close"],
                    start_time=current_time,
                    end_time=current_time
                )
                
                if not price_data.empty:
                    current_price = price_data["$close"].iloc[-1]
                    position_size = self.current_positions.get(asset, 0)
                    
                    if position_size < 0:  # Short position
                        position_value = abs(position_size) * entry_price
                        current_value = abs(position_size) * current_price
                        pnl = position_value - current_value  # Profit when price goes down
                        total_pnl += pnl
            
            return total_pnl / portfolio_value if portfolio_value > 0 else 0.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating portfolio P&L: {e}")
            return 0.0
    
    def _get_tradeable_universe(self, current_time: pd.Timestamp) -> List[str]:
        """
        Get universe of tradeable cryptocurrencies.
        
        Returns a list of cryptocurrency symbols that meet basic trading criteria:
        - Active trading
        - Sufficient market data
        - Not BTC (since we hold BTC spot)
        """
        # This would typically query from your crypto data provider
        # For now, return a placeholder universe
        universe = [
            "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "DOT", "AVAX", 
            "SHIB", "LTC", "LINK", "UNI", "ATOM", "NEAR", "ALGO",
            "VET", "ICP", "FIL", "HBAR", "EOS", "AAVE", "GRT"
        ]
        
        # Filter out assets with insufficient data
        valid_universe = []
        for asset in universe:
            try:
                # Check if we have sufficient historical data
                data = D.features(
                    instruments=[asset],
                    fields=["$close", "$volume"],
                    start_time=current_time - timedelta(days=self.config.factor_lookback_days),
                    end_time=current_time
                )
                if len(data) >= self.config.factor_lookback_days * 20:  # ~20 hours per day
                    valid_universe.append(asset)
            except:
                continue
        
        return valid_universe
    
    def _compute_factor_scores(self, universe: List[str], current_time: pd.Timestamp) -> Dict[str, float]:
        """
        Compute aggregated factor scores for all assets in universe.
        
        Returns a dictionary mapping asset symbols to factor scores.
        Higher scores indicate stronger short signals.
        """
        factor_scores = {}
        
        # Get factor expressions from our crypto factor library
        expressions, names = self.factor_library.get_factor_expressions()
        
        for asset in universe:
            try:
                # Compute factors for this asset
                factor_data = D.features(
                    instruments=[asset],
                    fields=expressions,
                    start_time=current_time - timedelta(days=self.config.factor_lookback_days),
                    end_time=current_time
                )
                
                if factor_data.empty:
                    factor_scores[asset] = 0.0
                    continue
                
                # Get latest factor values
                latest_factors = factor_data.iloc[-1]
                
                # Aggregate factor scores by category
                category_scores = {}
                
                # Group factors by category and compute weighted scores
                for category in self.config.factor_categories:
                    category_factors = [name for name in names if category.value.upper() in name]
                    if category_factors:
                        category_values = latest_factors[category_factors]
                        # Remove any NaN values
                        category_values = category_values.dropna()
                        if len(category_values) > 0:
                            category_scores[category.value] = category_values.mean()
                        else:
                            category_scores[category.value] = 0.0
                    else:
                        category_scores[category.value] = 0.0
                
                # Compute weighted final score
                final_score = 0.0
                for category, weight in self.config.factor_weights.items():
                    if category in category_scores:
                        final_score += weight * category_scores[category]
                
                factor_scores[asset] = final_score
                
            except Exception as e:
                warnings.warn(f"Error computing factors for {asset}: {e}")
                factor_scores[asset] = 0.0
        
        return factor_scores
    
    def _apply_liquidity_filter(self, universe: List[str], current_time: pd.Timestamp) -> List[str]:
        """
        Filter assets based on realistic liquidity requirements using available data.
        
        Since bid-ask spread and market cap data are not available in the current
        data collector, we use alternative metrics:
        - Volume-based liquidity assessment
        - Price spread estimation from high-low range
        - Trading activity consistency
        """
        liquid_assets = []
        
        for asset in universe:
            try:
                # Get recent trading data (7 days for stability)
                data = D.features(
                    instruments=[asset],
                    fields=["$close", "$volume", "$high", "$low"],
                    start_time=current_time - timedelta(days=7),
                    end_time=current_time
                )
                
                if data.empty or len(data) < 24:  # Need at least 24 hours of data
                    continue
                
                # Calculate volume-based liquidity
                recent_volume = data["$volume"].tail(24).mean()  # 24h average volume
                recent_price = data["$close"].iloc[-1]
                daily_volume_usd = recent_volume * recent_price
                
                # Volume filter: minimum daily volume
                if daily_volume_usd < self.config.min_daily_volume:
                    continue
                
                # Estimate spread from high-low range (proxy for bid-ask spread)
                high_low_spread = (data["$high"] - data["$low"]) / data["$close"]
                avg_spread_pct = high_low_spread.tail(24).mean() * 100
                
                # Spread filter: avoid assets with excessive price volatility
                if avg_spread_pct > self.config.max_spread_estimate:
                    continue
                
                # Trading activity consistency check
                volume_std = data["$volume"].tail(24).std()
                volume_mean = data["$volume"].tail(24).mean()
                volume_cv = volume_std / volume_mean if volume_mean > 0 else float('inf')
                
                # Activity filter: avoid assets with erratic trading patterns
                if volume_cv > 2.0:  # Coefficient of variation > 2.0 indicates erratic trading
                    continue
                
                # Additional check: ensure recent trading activity
                recent_volumes = data["$volume"].tail(6)  # Last 6 hours
                if (recent_volumes == 0).sum() > 2:  # More than 2 hours with zero volume
                    continue
                
                liquid_assets.append(asset)
                    
            except Exception as e:
                warnings.warn(f"Error checking liquidity for {asset}: {e}")
                continue
        
        return liquid_assets
    
    def _select_short_candidates(self, factor_scores: Dict[str, float], 
                               liquid_assets: List[str], current_time: pd.Timestamp) -> List[str]:
        """
        Select top candidates for shorting based on factor scores and liquidity.
        
        Returns a ranked list of assets to short.
        """
        # Filter factor scores to only include liquid assets
        liquid_scores = {asset: score for asset, score in factor_scores.items() 
                        if asset in liquid_assets}
        
        # Sort by factor score (higher scores = stronger short signals)
        sorted_assets = sorted(liquid_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top N candidates
        top_candidates = [asset for asset, score in sorted_assets[:self.config.num_short_positions]]
        
        return top_candidates
    
    def _calculate_position_sizes(self, short_candidates: List[str], 
                                factor_scores: Dict[str, float], 
                                current_time: pd.Timestamp) -> Dict[str, float]:
        """
        Calculate position sizes for selected short candidates with enhanced allocation strategies.
        
        Parameters
        ----------
        short_candidates : List[str]
            List of assets selected for shorting
        factor_scores : Dict[str, float]
            Factor scores for each asset
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        Dict[str, float]
            Dictionary mapping asset symbols to position sizes (as fraction of short pool)
        """
        position_sizes = {}
        
        if not short_candidates:
            return position_sizes
        
        if self.config.weighting_scheme == WeightingScheme.EQUAL_WEIGHT:
            # Equal weight allocation
            weight_per_asset = 1.0 / len(short_candidates)
            for asset in short_candidates:
                position_sizes[asset] = weight_per_asset
                
        elif self.config.weighting_scheme == WeightingScheme.FACTOR_WEIGHTED:
            # Enhanced factor-based weighting with normalization
            position_sizes = self._calculate_factor_weighted_positions(short_candidates, factor_scores)
                    
        elif self.config.weighting_scheme == WeightingScheme.VOLATILITY_WEIGHTED:
            # Enhanced volatility-based weighting
            position_sizes = self._calculate_volatility_weighted_positions(short_candidates, current_time)
            
        elif self.config.weighting_scheme == WeightingScheme.RISK_PARITY:
            # Risk parity allocation based on multiple risk metrics
            position_sizes = self._calculate_risk_parity_positions(short_candidates, current_time)
        
        # Apply position concentration limits and risk controls
        position_sizes = self._apply_position_limits(position_sizes)
        
        return position_sizes
    
    def _calculate_factor_weighted_positions(self, short_candidates: List[str], 
                                           factor_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate factor-weighted positions with enhanced score normalization.
        
        Parameters
        ----------
        short_candidates : List[str]
            List of assets selected for shorting
        factor_scores : Dict[str, float]
            Factor scores for each asset
            
        Returns
        -------
        Dict[str, float]
            Position weights based on factor scores
        """
        position_sizes = {}
        
        # Get scores for candidates only
        candidate_scores = [factor_scores.get(asset, 0.0) for asset in short_candidates]
        
        # Convert to positive weights (higher score = higher weight)
        if max(candidate_scores) > 0:
            # Use softmax for score normalization to avoid extreme weights
            exp_scores = np.exp(np.array(candidate_scores))
            softmax_weights = exp_scores / np.sum(exp_scores)
            
            for i, asset in enumerate(short_candidates):
                position_sizes[asset] = softmax_weights[i]
        else:
            # Fallback to equal weight if all scores are zero/negative
            weight_per_asset = 1.0 / len(short_candidates)
            for asset in short_candidates:
                position_sizes[asset] = weight_per_asset
        
        return position_sizes
    
    def _calculate_volatility_weighted_positions(self, short_candidates: List[str], 
                                               current_time: pd.Timestamp) -> Dict[str, float]:
        """
        Calculate volatility-weighted positions with enhanced risk metrics.
        
        Parameters
        ----------
        short_candidates : List[str]
            List of assets selected for shorting
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        Dict[str, float]
            Position weights based on inverse volatility
        """
        position_sizes = {}
        volatilities = {}
        
        for asset in short_candidates:
            try:
                # Get price data for volatility calculation
                data = D.features(
                    instruments=[asset],
                    fields=["$close"],
                    start_time=current_time - timedelta(days=self.config.volatility_lookback),
                    end_time=current_time
                )
                
                if not data.empty and len(data) > 10:
                    returns = data["$close"].pct_change().dropna()
                    
                    # Calculate realized volatility (annualized)
                    volatility = returns.std() * np.sqrt(24 * 365)  # Annualized volatility
                    
                    # Add downside volatility (more relevant for short positions)
                    downside_returns = returns[returns < 0]
                    downside_vol = downside_returns.std() * np.sqrt(24 * 365) if len(downside_returns) > 0 else volatility
                    
                    # Combine both metrics
                    combined_vol = 0.7 * volatility + 0.3 * downside_vol
                    volatilities[asset] = combined_vol
                else:
                    volatilities[asset] = 0.5  # Default volatility
            except:
                volatilities[asset] = 0.5  # Default volatility
        
        # Calculate inverse volatility weights
        inv_vol_weights = {asset: 1.0 / max(vol, 0.01) for asset, vol in volatilities.items()}
        total_inv_vol = sum(inv_vol_weights.values())
        
        for asset in short_candidates:
            position_sizes[asset] = inv_vol_weights[asset] / total_inv_vol
        
        return position_sizes
    
    def _calculate_risk_parity_positions(self, short_candidates: List[str], 
                                       current_time: pd.Timestamp) -> Dict[str, float]:
        """
        Calculate risk parity positions based on multiple risk metrics.
        
        Parameters
        ----------
        short_candidates : List[str]
            List of assets selected for shorting
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        Dict[str, float]
            Position weights based on risk parity
        """
        position_sizes = {}
        risk_metrics = {}
        
        for asset in short_candidates:
            try:
                # Get extended data for risk calculation
                data = D.features(
                    instruments=[asset],
                    fields=["$close", "$volume", "$high", "$low"],
                    start_time=current_time - timedelta(days=self.config.volatility_lookback),
                    end_time=current_time
                )
                
                if not data.empty and len(data) > 10:
                    # Calculate multiple risk metrics
                    returns = data["$close"].pct_change().dropna()
                    
                    # 1. Price volatility
                    price_vol = returns.std() * np.sqrt(24 * 365)
                    
                    # 2. Volume volatility (liquidity risk)
                    volume_vol = data["$volume"].pct_change().std() * np.sqrt(24 * 365)
                    
                    # 3. High-low spread volatility (market impact risk)
                    spread = (data["$high"] - data["$low"]) / data["$close"]
                    spread_vol = spread.std() * np.sqrt(24 * 365)
                    
                    # 4. Tail risk (VaR at 5% level)
                    var_5pct = np.percentile(returns, 5)
                    
                    # Combine risk metrics with weights
                    combined_risk = (0.4 * price_vol + 
                                   0.2 * volume_vol + 
                                   0.2 * spread_vol + 
                                   0.2 * abs(var_5pct))
                    
                    risk_metrics[asset] = combined_risk
                else:
                    risk_metrics[asset] = 0.5  # Default risk
            except:
                risk_metrics[asset] = 0.5  # Default risk
        
        # Calculate risk parity weights (inverse risk)
        inv_risk_weights = {asset: 1.0 / max(risk, 0.01) for asset, risk in risk_metrics.items()}
        total_inv_risk = sum(inv_risk_weights.values())
        
        for asset in short_candidates:
            position_sizes[asset] = inv_risk_weights[asset] / total_inv_risk
        
        return position_sizes
    
    def _apply_position_limits(self, position_sizes: Dict[str, float]) -> Dict[str, float]:
        """
        Apply position concentration limits and other risk controls.
        
        Parameters
        ----------
        position_sizes : Dict[str, float]
            Raw position sizes
            
        Returns
        -------
        Dict[str, float]
            Position sizes after applying limits
        """
        # Apply position concentration limits
        max_weight = self.config.position_concentration_limit
        limited_sizes = {}
        
        for asset, size in position_sizes.items():
            limited_sizes[asset] = min(size, max_weight)
        
        # Renormalize to sum to 1
        total_weight = sum(limited_sizes.values())
        if total_weight > 0:
            for asset in limited_sizes:
                limited_sizes[asset] /= total_weight
        
        return limited_sizes
    
    def _generate_orders(self, position_sizes: Dict[str, float], 
                        current_time: pd.Timestamp) -> List[Order]:
        """
        Generate actual trading orders based on position sizes.
        
        This method handles both BTC spot allocation and short pool orders.
        
        Returns
        -------
        List[Order]
            List of Order objects for execution
        """
        orders = []
        
        # Get current portfolio value (this would come from actual account)
        total_portfolio_value = self._get_portfolio_value()
        
        # Calculate allocation amounts
        btc_spot_value = total_portfolio_value * self.config.btc_spot_ratio
        short_pool_value = total_portfolio_value * self.config.short_pool_ratio
        
        self.logger.info(f"Portfolio allocation: BTC Spot=${btc_spot_value:,.0f} ({self.config.btc_spot_ratio:.1%}), "
                        f"Short Pool=${short_pool_value:,.0f} ({self.config.short_pool_ratio:.1%})")
        
        # 1. Generate BTC spot position order
        btc_order = self._generate_btc_spot_order(btc_spot_value, current_time)
        if btc_order:
            orders.append(btc_order)
        
        # 2. Generate short pool orders
        short_orders = self._generate_short_pool_orders(position_sizes, short_pool_value, current_time)
        orders.extend(short_orders)
        
        return orders
    
    def _get_portfolio_value(self) -> float:
        """
        Get current portfolio value.
        
        In a real implementation, this would query the trading account.
        For simulation, we use a placeholder value.
        """
        # Placeholder: In production, this would query actual account balance
        return 1000000  # $1M portfolio
    
    def _generate_btc_spot_order(self, btc_allocation: float, current_time: pd.Timestamp) -> Optional[Order]:
        """
        Generate BTC spot position order.
        
        Parameters
        ----------
        btc_allocation : float
            USD value to allocate to BTC spot
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        Optional[Order]
            BTC spot order or None if error
        """
        try:
            # Get current BTC price
            btc_price_data = D.features(
                instruments=["BTC"],
                fields=["$close"],
                start_time=current_time,
                end_time=current_time
            )
            
            if btc_price_data.empty:
                self.logger.warning("Cannot get BTC price for spot allocation")
                return None
            
            current_btc_price = btc_price_data["$close"].iloc[-1]
            btc_amount = btc_allocation / current_btc_price
            
            # Create BTC spot buy order
            btc_order = Order(
                stock_id="BTC",
                amount=btc_amount,  # Positive for long position
                start_time=current_time,
                end_time=current_time,
                factor=current_btc_price
            )
            
            self.logger.info(f"BTC spot order: {btc_amount:.6f} BTC at ${current_btc_price:,.0f}")
            return btc_order
            
        except Exception as e:
            self.logger.error(f"Error generating BTC spot order: {e}")
            return None
    
    def _generate_short_pool_orders(self, position_sizes: Dict[str, float], 
                                  short_pool_value: float, 
                                  current_time: pd.Timestamp) -> List[Order]:
        """
        Generate orders for short pool positions.
        
        Parameters
        ----------
        position_sizes : Dict[str, float]
            Position weights for each asset
        short_pool_value : float
            Total value allocated to short pool
        current_time : pd.Timestamp
            Current timestamp
            
        Returns
        -------
        List[Order]
            List of short orders
        """
        orders = []
        
        for asset, weight in position_sizes.items():
            try:
                # Get current price
                price_data = D.features(
                    instruments=[asset],
                    fields=["$close"],
                    start_time=current_time,
                    end_time=current_time
                )
                
                if price_data.empty:
                    self.logger.warning(f"Cannot get price for {asset}")
                    continue
                
                current_price = price_data["$close"].iloc[-1]
                
                # Calculate order amount
                position_value = short_pool_value * weight
                share_amount = -position_value / current_price  # Negative for short position
                
                # Apply minimum position size filter
                if abs(position_value) < 1000:  # Minimum $1000 position
                    continue
                
                # Create short order
                order = Order(
                    stock_id=asset,
                    amount=share_amount,
                    start_time=current_time,
                    end_time=current_time,
                    factor=current_price
                )
                orders.append(order)
                
                self.logger.info(f"Short order: {asset} ${position_value:,.0f} ({weight:.1%}) at ${current_price:.4f}")
                
            except Exception as e:
                self.logger.warning(f"Error generating order for {asset}: {e}")
                continue
        
        return orders
    
    def _update_position_history(self, short_candidates: List[str], 
                               position_sizes: Dict[str, float], 
                               current_time: pd.Timestamp):
        """Update position history for performance tracking."""
        self.position_history.append({
            'timestamp': current_time,
            'rebalance_count': self.rebalance_count,
            'short_candidates': short_candidates.copy(),
            'position_sizes': position_sizes.copy(),
            'num_positions': len(short_candidates)
        })
        
        # Keep only recent history (last 100 rebalances)
        if len(self.position_history) > 100:
            self.position_history = self.position_history[-100:]
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive strategy statistics and performance metrics.
        
        Returns
        -------
        Dict[str, Any]
            Dictionary containing strategy performance statistics
        """
        stats = {
            'rebalance_count': self.rebalance_count,
            'last_rebalance_time': self.last_rebalance_time,
            'config': {
                'rebalance_frequency': self.config.rebalance_frequency.value,
                'num_short_positions': self.config.num_short_positions,
                'btc_spot_ratio': self.config.btc_spot_ratio,
                'weighting_scheme': self.config.weighting_scheme.value,
                'factor_categories': [cat.value for cat in self.config.factor_categories]
            }
        }
        
        if self.position_history:
            recent_positions = self.position_history[-10:]  # Last 10 rebalances
            stats['recent_performance'] = {
                'avg_num_positions': np.mean([pos['num_positions'] for pos in recent_positions]),
                'position_turnover': self._calculate_position_turnover(),
                'most_frequent_shorts': self._get_most_frequent_positions()
            }
        
        return stats
    
    def _calculate_position_turnover(self) -> float:
        """Calculate position turnover rate."""
        if len(self.position_history) < 2:
            return 0.0
        
        turnovers = []
        for i in range(1, min(len(self.position_history), 11)):  # Last 10 periods
            prev_positions = set(self.position_history[-i-1]['short_candidates'])
            curr_positions = set(self.position_history[-i]['short_candidates'])
            
            intersection = len(prev_positions.intersection(curr_positions))
            union = len(prev_positions.union(curr_positions))
            
            if union > 0:
                turnover = 1.0 - (intersection / len(prev_positions))
                turnovers.append(turnover)
        
        return np.mean(turnovers) if turnovers else 0.0
    
    def _get_most_frequent_positions(self) -> List[Tuple[str, int]]:
        """Get most frequently shorted assets."""
        if not self.position_history:
            return []
        
        asset_counts = {}
        recent_history = self.position_history[-20:]  # Last 20 rebalances
        
        for position_record in recent_history:
            for asset in position_record['short_candidates']:
                asset_counts[asset] = asset_counts.get(asset, 0) + 1
        
        # Sort by frequency
        sorted_assets = sorted(asset_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_assets[:10]  # Top 10 most frequent


# Convenience function for strategy creation
def create_btcdom2_strategy(
    rebalance_frequency: str = "8h",
    num_short_positions: int = 10,
    btc_spot_ratio: float = 0.5,
    weighting_scheme: str = "factor_weighted",
    factor_categories: Optional[List[str]] = None,
    **kwargs
) -> BtcDom2Strategy:
    """
    Convenience function to create a BTC Dominance strategy.
    
    Parameters
    ----------
    rebalance_frequency : str, default "8h"
        Rebalancing frequency: "4h", "8h", "12h", "1d"
    num_short_positions : int, default 10
        Number of altcoins to short (5-20)
    btc_spot_ratio : float, default 0.5
        Proportion allocated to BTC spot (0.3-0.7)
    weighting_scheme : str, default "factor_weighted"
        Position weighting scheme: "equal_weight", "factor_weighted", "volatility_weighted"
    factor_categories : List[str], optional
        Factor categories to use. If None, uses default categories.
    **kwargs
        Additional configuration parameters
        
    Returns
    -------
    BtcDom2Strategy
        Configured BTC Dominance strategy instance
    """
    # Convert string enums
    rebal_freq = RebalanceFrequency(rebalance_frequency)
    weight_scheme = WeightingScheme(weighting_scheme)
    
    # Convert factor categories
    if factor_categories is None:
        factor_cats = [FactorCategory.DECLINE, FactorCategory.VOLUME, 
                      FactorCategory.MOMENTUM, FactorCategory.FUNDING]
    else:
        factor_cats = [FactorCategory(cat) for cat in factor_categories]
    
    # Create configuration
    config = BtcDom2Config(
        rebalance_frequency=rebal_freq,
        num_short_positions=num_short_positions,
        btc_spot_ratio=btc_spot_ratio,
        short_pool_ratio=1.0 - btc_spot_ratio,
        weighting_scheme=weight_scheme,
        factor_categories=factor_cats,
        **kwargs
    )
    
    return BtcDom2Strategy(config=config)