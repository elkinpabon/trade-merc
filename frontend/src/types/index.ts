export type TradingMode = 'paper' | 'live';
export type BotStatus = 'RUNNING' | 'STOPPED' | 'ERROR' | 'PAUSED';

export interface BotConfigData {
  id: number;
  name: string;
  exchange_id: string;
  mode: TradingMode;
  symbols: string[];
  timeframe: string;
  virtual_balance: number;
  ema_fast_period: number;
  ema_slow_period: number;
  rsi_period: number;
  rsi_entry_threshold: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  risk_per_trade_pct: number;
  slippage_pct: number;
  fee_pct: number;
  cooldown_seconds: number;
  candle_limit: number;
  polling_interval_seconds: number;
  is_active: boolean;
  updated_at?: string;
}

export interface PaperPositionData {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  is_open: boolean;
  opened_at: string;
}

export interface TradeData {
  id: string;
  symbol: string;
  side: string;
  entry_order_id?: string;
  exit_order_id?: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  realized_pnl: number;
  realized_pnl_pct: number;
  total_fee: number;
  exit_reason: string;
  opened_at: string;
  closed_at: string;
}

export interface SignalData {
  id: string;
  bot_run_id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  action: string;
  price: number;
  reason: string;
  indicators: Record<string, any>;
  status: 'PENDING' | 'EXECUTED' | 'REJECTED';
  timestamp: string;
}

export interface PaperOrderData {
  id: string;
  signal_id?: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  requested_price: number;
  status: string;
  simulated_fee: number;
  simulated_slippage: number;
  rejection_reason?: string;
  created_at: string;
}

export interface PaperFillData {
  id: string;
  order_id: string;
  symbol: string;
  side: string;
  fill_price: number;
  fill_quantity: number;
  fee_amount: number;
  fee_currency: string;
  timestamp: string;
}

export interface PortfolioSummaryData {
  cash_balance: number;
  positions_value: number;
  total_equity: number;
  realized_pnl: number;
  unrealized_pnl: number;
  peak_equity: number;
  drawdown_pct: number;
  total_trades: number;
  win_rate: number;
  open_positions_count: number;
  positions: PaperPositionData[];
  recent_trades: TradeData[];
}

export interface RiskAlertData {
  id?: number;
  event_type: string;
  symbol?: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface BotLogData {
  id: number;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  module: string;
  message: string;
  timestamp: string;
}

export interface CandleData {
  symbol: string;
  timeframe: string;
  timestamp: number;
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SystemHealthData {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  components: {
    id: number;
    component: string;
    status: 'HEALTHY' | 'DEGRADED' | 'DOWN' | 'IDLE';
    details: string;
    last_check: string;
  }[];
}

export interface AnalyticsOverviewData {
  overview: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    profit_factor: number;
    total_pnl: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
  };
  equity_curve: { timestamp: string; equity: number; drawdown: number }[];
  symbol_breakdown: { symbol: string; trades: number; pnl: number; win_rate: number }[];
  experiment: { id: string; status: string; started_at: string } | null;
}

export interface ExperimentReportData {
  run: {
    id: string;
    status: string;
    model_version_id: string;
    symbols: string[];
    timeframe: string;
    started_at: string;
    planned_end_at: string;
    finished_at: string | null;
  };
  coverage: {
    target_days: number;
    elapsed_days: number;
    progress_pct: number;
    days_with_metrics: number;
    coverage_pct: number;
    expected_cycles: number;
    recorded_cycles: number;
    successful_cycles: number;
    cycle_coverage_pct: number;
  };
  funnel: {
    evaluations: number;
    signals: number;
    orders: number;
    filled_orders: number;
    fills: number;
    closed_trades: number;
  };
  performance: {
    net_pnl: number;
    gross_pnl_before_fees: number;
    profit_factor: number | null;
    expectancy: number;
    fees: number;
    wins: number;
    losses: number;
    max_drawdown_pct: number;
  };
  evaluability: {
    evaluable: boolean;
    criteria: Record<string, boolean>;
  };
}
