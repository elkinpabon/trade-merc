import pandas as pd
import numpy as np

class IndicatorService:
    """
    Advanced Multi-Factor Technical Analysis Indicator Engine.
    Computes EMA, RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic RSI,
    OBV, VWAP, and Volume Profile for comprehensive market scoring.
    All calculations are pure pandas/numpy — no external TA library needed.
    """

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Calculates Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculates Relative Strength Index (RSI)."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculates MACD line, Signal line, and Histogram."""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
        """Calculates Bollinger Bands (Upper, Middle, Lower)."""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper.fillna(series), middle.fillna(series), lower.fillna(series)

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average True Range (ATR) for volatility measurement."""
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr.fillna(true_range)

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average Directional Index (ADX) for trend strength."""
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        close_prev = close.shift(1)
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr_smooth = true_range.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_smooth.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_smooth.replace(0, np.nan))

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.rolling(window=period).mean()
        return adx.fillna(0.0)

    @staticmethod
    def calculate_stochastic_rsi(series: pd.Series, rsi_period: int = 14, stoch_period: int = 14,
                                  smooth_k: int = 3, smooth_d: int = 3):
        """Calculates Stochastic RSI (%K and %D lines)."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50.0)

        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()
        stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)) * 100
        stoch_rsi = stoch_rsi.fillna(50.0)

        k_line = stoch_rsi.rolling(window=smooth_k).mean().fillna(50.0)
        d_line = k_line.rolling(window=smooth_d).mean().fillna(50.0)
        return k_line, d_line

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """Calculates On-Balance Volume (OBV)."""
        close_diff = df['close'].diff()
        direction = np.where(close_diff > 0, 1, np.where(close_diff < 0, -1, 0))
        obv = (df['volume'] * direction).cumsum()
        return pd.Series(obv, index=df.index)

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """Calculates Volume Weighted Average Price (VWAP) approximation."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        cum_vol = df['volume'].cumsum()
        cum_tp_vol = (typical_price * df['volume']).cumsum()
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
        return vwap.fillna(typical_price)

    @classmethod
    def apply_indicators(
        cls,
        df: pd.DataFrame,
        ema_fast: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14
    ) -> pd.DataFrame:
        """Applies the full suite of advanced technical indicators to a DataFrame."""
        if df.empty or len(df) < max(ema_slow, rsi_period, 26):
            return df

        df = df.copy()

        # Core EMAs
        df['ema_fast'] = cls.calculate_ema(df['close'], period=ema_fast)
        df['ema_slow'] = cls.calculate_ema(df['close'], period=ema_slow)

        # RSI
        df['rsi'] = cls.calculate_rsi(df['close'], period=rsi_period)

        # MACD (12, 26, 9)
        df['macd_line'], df['macd_signal'], df['macd_histogram'] = cls.calculate_macd(df['close'])

        # Bollinger Bands (20, 2)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = cls.calculate_bollinger_bands(df['close'])

        # ATR (14)
        df['atr'] = cls.calculate_atr(df, period=14)

        # ADX (14)
        df['adx'] = cls.calculate_adx(df, period=14)

        # Stochastic RSI
        df['stoch_rsi_k'], df['stoch_rsi_d'] = cls.calculate_stochastic_rsi(df['close'])

        # OBV
        df['obv'] = cls.calculate_obv(df)

        # VWAP
        df['vwap'] = cls.calculate_vwap(df)

        # Volume Profile (relative to 20-period SMA)
        df['vol_sma'] = df['volume'].rolling(window=20).mean().fillna(df['volume'])
        df['vol_ratio'] = (df['volume'] / df['vol_sma'].replace(0, np.nan)).fillna(1.0)

        # Crossover Detection
        df['prev_ema_fast'] = df['ema_fast'].shift(1)
        df['prev_ema_slow'] = df['ema_slow'].shift(1)
        df['bullish_cross'] = (df['prev_ema_fast'] <= df['prev_ema_slow']) & (df['ema_fast'] > df['ema_slow'])
        df['bearish_cross'] = (df['prev_ema_fast'] >= df['prev_ema_slow']) & (df['ema_fast'] < df['ema_slow'])

        # MACD crossover
        df['prev_macd'] = df['macd_line'].shift(1)
        df['prev_macd_signal'] = df['macd_signal'].shift(1)
        df['macd_bullish_cross'] = (df['prev_macd'] <= df['prev_macd_signal']) & (df['macd_line'] > df['macd_signal'])

        # Bollinger Band width (squeeze detection)
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle'].replace(0, np.nan)).fillna(0.0)

        return df
