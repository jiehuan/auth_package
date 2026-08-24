#!/usr/bin/env python3
"""
Generate an OpenAPI 3.0.1 specification for the Alpha Vantage API,
shaped for onboarding into Azure API Management.

Design note
-----------
Alpha Vantage exposes every capability on a single backend route:
    GET https://www.alphavantage.co/query?function=<FUNCTION>&...
OpenAPI cannot express many operations on one path+method, so this spec
promotes each `function` to its own path (/TIME_SERIES_DAILY, /GLOBAL_QUOTE, ...).
An API-level APIM policy rewrites the path back to /query and injects
`function` + the upstream `apikey`.
"""

import yaml
from collections import OrderedDict

# --------------------------------------------------------------------------
# Reusable parameter definitions (emitted into components.parameters)
# --------------------------------------------------------------------------

COMMON_PARAMS = {
    "symbol": {
        "name": "symbol", "in": "query", "required": True,
        "description": "Ticker of the equity, e.g. `IBM`. Non-US listings use a suffix, e.g. `TSCO.LON`, `RELIANCE.BSE`, `600104.SHH`.",
        "schema": {"type": "string"}, "example": "IBM",
    },
    "symbolBulk": {
        "name": "symbol", "in": "query", "required": True,
        "description": "Up to 100 comma-separated symbols. Symbols beyond the first 100 are ignored.",
        "schema": {"type": "string"}, "example": "MSFT,AAPL,IBM",
    },
    "keywords": {
        "name": "keywords", "in": "query", "required": True,
        "description": "Free-text search string.",
        "schema": {"type": "string"}, "example": "microsoft",
    },
    "intervalIntraday": {
        "name": "interval", "in": "query", "required": True,
        "description": "Spacing between consecutive data points.",
        "schema": {"type": "string", "enum": ["1min", "5min", "15min", "30min", "60min"]},
        "example": "5min",
    },
    "intervalIndex": {
        "name": "interval", "in": "query", "required": True,
        "description": "Temporal resolution of the index time series.",
        "schema": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
        "example": "weekly",
    },
    "intervalIndicator": {
        "name": "interval", "in": "query", "required": True,
        "description": "Spacing between consecutive data points in the indicator series.",
        "schema": {"type": "string",
                   "enum": ["1min", "5min", "15min", "30min", "60min", "daily", "weekly", "monthly"]},
        "example": "daily",
    },
    "intervalEconomic": {
        "name": "interval", "in": "query", "required": False,
        "description": "Reporting frequency.",
        "schema": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "annual"]},
    },
    "month": {
        "name": "month", "in": "query", "required": False,
        "description": "Query a specific historical month in `YYYY-MM` format. Any month from `2000-01` onward is supported. Intraday resolutions only.",
        "schema": {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"},
        "example": "2009-01",
    },
    "outputsize": {
        "name": "outputsize", "in": "query", "required": False,
        "description": "`compact` returns the latest 100 points; `full` returns the complete series. `full` requires a premium upstream key on several endpoints.",
        "schema": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
    },
    "datatype": {
        "name": "datatype", "in": "query", "required": False,
        "description": "Response encoding. `csv` changes the response media type to `text/csv`.",
        "schema": {"type": "string", "enum": ["json", "csv"], "default": "json"},
    },
    "adjusted": {
        "name": "adjusted", "in": "query", "required": False,
        "description": "When `true` the series is adjusted for historical splits and dividends.",
        "schema": {"type": "boolean", "default": True},
    },
    "extendedHours": {
        "name": "extended_hours", "in": "query", "required": False,
        "description": "When `true` the series includes pre-market and post-market bars (04:00-20:00 ET for US markets).",
        "schema": {"type": "boolean", "default": True},
    },
    "entitlement": {
        "name": "entitlement", "in": "query", "required": False,
        "description": "Controls data freshness. Omit for end-of-day data. `realtime` and `delayed` require an entitled upstream subscription and are subject to exchange/FINRA/SEC market-data rules.",
        "schema": {"type": "string", "enum": ["realtime", "delayed"]},
    },
    "seriesType": {
        "name": "series_type", "in": "query", "required": True,
        "description": "Price series the indicator is computed on.",
        "schema": {"type": "string", "enum": ["close", "open", "high", "low"]},
        "example": "close",
    },
    "timePeriod": {
        "name": "time_period", "in": "query", "required": True,
        "description": "Number of data points used to calculate each value.",
        "schema": {"type": "integer", "minimum": 1}, "example": 60,
    },
    "fromCurrency": {
        "name": "from_currency", "in": "query", "required": True,
        "description": "Source currency; accepts both physical (`USD`) and digital (`BTC`) currency codes.",
        "schema": {"type": "string"}, "example": "USD",
    },
    "toCurrency": {
        "name": "to_currency", "in": "query", "required": True,
        "description": "Destination currency; accepts both physical and digital currency codes.",
        "schema": {"type": "string"}, "example": "JPY",
    },
    "fromSymbol": {
        "name": "from_symbol", "in": "query", "required": True,
        "description": "Base currency of the FX pair, as a three-letter code.",
        "schema": {"type": "string"}, "example": "EUR",
    },
    "toSymbol": {
        "name": "to_symbol", "in": "query", "required": True,
        "description": "Quote currency of the FX pair, as a three-letter code.",
        "schema": {"type": "string"}, "example": "USD",
    },
    "cryptoSymbol": {
        "name": "symbol", "in": "query", "required": True,
        "description": "Digital currency code, e.g. `BTC`.",
        "schema": {"type": "string"}, "example": "BTC",
    },
    "market": {
        "name": "market", "in": "query", "required": True,
        "description": "Exchange market to quote the digital currency in, e.g. `USD`, `EUR`, `CNY`.",
        "schema": {"type": "string"}, "example": "USD",
    },
    "commodityInterval": {
        "name": "interval", "in": "query", "required": False,
        "description": "Reporting frequency for the commodity series.",
        "schema": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "annual"],
                   "default": "monthly"},
    },
}

# --------------------------------------------------------------------------
# Non-indicator operations
# key: (path, operationId, tag, summary, description, [param refs], premium)
# --------------------------------------------------------------------------

OPERATIONS = [
    # ---------------- Core Stock ----------------
    ("TIME_SERIES_INTRADAY", "getTimeSeriesIntraday", "Core Stock",
     "Intraday OHLCV time series",
     "Current and 20+ years of historical intraday OHLCV candles for the specified equity, covering pre-market and post-market sessions where applicable. Both raw (as-traded) and split/dividend-adjusted values can be requested.",
     ["symbol", "intervalIntraday", "adjusted", "extendedHours", "month", "outputsize", "datatype", "entitlement"],
     True),
    ("TIME_SERIES_DAILY", "getTimeSeriesDaily", "Core Stock",
     "Daily OHLCV time series",
     "Raw (as-traded) daily OHLCV candles covering 20+ years of history. Use TIME_SERIES_DAILY_ADJUSTED if you need adjusted closes and corporate-action detail.",
     ["symbol", "outputsize", "datatype"], False),
    ("TIME_SERIES_DAILY_ADJUSTED", "getTimeSeriesDailyAdjusted", "Core Stock",
     "Daily adjusted OHLCV time series",
     "Daily OHLCV plus adjusted close and the historical split/dividend events behind the adjustment, covering 20+ years of history.",
     ["symbol", "outputsize", "datatype", "entitlement"], True),
    ("TIME_SERIES_WEEKLY", "getTimeSeriesWeekly", "Core Stock",
     "Weekly OHLCV time series",
     "Weekly OHLCV candles keyed on the last trading day of each week, covering 20+ years of history.",
     ["symbol", "datatype"], False),
    ("TIME_SERIES_WEEKLY_ADJUSTED", "getTimeSeriesWeeklyAdjusted", "Core Stock",
     "Weekly adjusted OHLCV time series",
     "Weekly OHLCV plus adjusted close and weekly dividend, covering 20+ years of history.",
     ["symbol", "datatype"], False),
    ("TIME_SERIES_MONTHLY", "getTimeSeriesMonthly", "Core Stock",
     "Monthly OHLCV time series",
     "Monthly OHLCV candles keyed on the last trading day of each month, covering 20+ years of history.",
     ["symbol", "datatype"], False),
    ("TIME_SERIES_MONTHLY_ADJUSTED", "getTimeSeriesMonthlyAdjusted", "Core Stock",
     "Monthly adjusted OHLCV time series",
     "Monthly OHLCV plus adjusted close and monthly dividend, covering 20+ years of history.",
     ["symbol", "datatype"], False),
    ("GLOBAL_QUOTE", "getGlobalQuote", "Core Stock",
     "Latest price and volume for one ticker",
     "Lightweight quote for a single ticker. For many tickers at once use REALTIME_BULK_QUOTES, which accepts up to 100 symbols per request.",
     ["symbol", "datatype", "entitlement"], False),
    ("REALTIME_BULK_QUOTES", "getRealtimeBulkQuotes", "Core Stock",
     "Realtime quotes in bulk (up to 100 symbols)",
     "Realtime quotes for US-traded symbols in bulk, covering regular and extended trading hours. A high-throughput alternative to GLOBAL_QUOTE.",
     ["symbolBulk", "datatype"], True),
    ("REALTIME_BULK_BID_ASK_PRICES", "getRealtimeBulkBidAsk", "Core Stock",
     "Realtime bid/ask prices in bulk (up to 100 symbols)",
     "Top-of-book bid and ask prices for US-traded symbols in bulk, covering regular and extended trading hours.",
     ["symbolBulk", "datatype"], True),
    ("SYMBOL_SEARCH", "searchSymbols", "Core Stock",
     "Ticker search",
     "Best-matching symbols and market metadata for a keyword string, each with a match score. Typically used to back an autocomplete experience.",
     ["keywords", "datatype"], False),
    ("MARKET_STATUS", "getMarketStatus", "Core Stock",
     "Global market open/close status",
     "Current open-versus-closed status of major equity, FX, and cryptocurrency trading venues worldwide.",
     [], False),

    # ---------------- Index Data ----------------
    ("INDEX_DATA", "getIndexData", "Index Data",
     "Index OHLC time series",
     "Decades of daily/weekly/monthly OHLC data for 200+ major indices. Well-known symbols include `DJI` (Dow Jones Industrial Average), `SPX` (S&P 500), `COMP` (Nasdaq Composite), `NDX` (Nasdaq-100), `VIX` (Cboe Volatility Index), and `RUT` (Russell 2000). Call INDEX_CATALOG for the full symbol list.",
     ["symbol", "intervalIndex", "datatype"], True),
    ("INDEX_CATALOG", "getIndexCatalog", "Index Data",
     "Supported index symbols",
     "Full list of supported index symbols with their long-form names.",
     ["datatype"], False),

    # ---------------- Options ----------------
    ("REALTIME_OPTIONS", "getRealtimeOptions", "Options",
     "Realtime options chain",
     "Realtime US options data covering the full chain for the specified underlying, with optional Greeks and implied volatility.",
     ["symbol", "datatype"], True),
    ("HISTORICAL_OPTIONS", "getHistoricalOptions", "Options",
     "Historical options chain",
     "Historical US options chain for the specified underlying on a given trading day, including Greeks and implied volatility.",
     ["symbol", "datatype"], False),

    # ---------------- Alpha Intelligence ----------------
    ("NEWS_SENTIMENT", "getNewsSentiment", "Alpha Intelligence",
     "Market news and sentiment scores",
     "Live and historical market news with article-level and ticker-level sentiment scoring, filterable by ticker, topic, and time window.",
     ["datatype"], False),
    ("EARNINGS_CALL_TRANSCRIPT", "getEarningsCallTranscript", "Alpha Intelligence",
     "Earnings call transcript",
     "Transcript of a company earnings call for a given quarter, annotated with LLM-based sentiment signals.",
     ["symbol", "datatype"], False),
    ("TOP_GAINERS_LOSERS", "getTopGainersLosers", "Alpha Intelligence",
     "Top gainers, losers, and most active tickers",
     "Top 20 gainers, losers, and most actively traded tickers in the US market.",
     ["datatype"], False),
    ("INSIDER_TRANSACTIONS", "getInsiderTransactions", "Alpha Intelligence",
     "Insider transactions",
     "Latest and historical insider transactions filed by key stakeholders of the specified company.",
     ["symbol", "datatype"], False),

    # ---------------- Fundamental Data ----------------
    ("OVERVIEW", "getCompanyOverview", "Fundamental Data",
     "Company overview",
     "Company profile and key financial ratios for the specified ticker.",
     ["symbol", "datatype"], False),
    ("ETF_PROFILE", "getEtfProfile", "Fundamental Data",
     "ETF profile and holdings",
     "Key ETF attributes — net assets, expense ratio, turnover — together with sector allocation and the full holdings list.",
     ["symbol", "datatype"], False),
    ("DIVIDENDS", "getDividends", "Fundamental Data",
     "Dividend history",
     "Historical and declared future dividend distributions for the specified ticker.",
     ["symbol", "datatype"], False),
    ("SPLITS", "getSplits", "Fundamental Data",
     "Split history",
     "Historical split events for the specified ticker.",
     ["symbol", "datatype"], False),
    ("INCOME_STATEMENT", "getIncomeStatement", "Fundamental Data",
     "Income statement",
     "Annual and quarterly income statements, normalised to a consistent schema across issuers.",
     ["symbol", "datatype"], False),
    ("BALANCE_SHEET", "getBalanceSheet", "Fundamental Data",
     "Balance sheet",
     "Annual and quarterly balance sheets, normalised to a consistent schema across issuers.",
     ["symbol", "datatype"], False),
    ("CASH_FLOW", "getCashFlow", "Fundamental Data",
     "Cash flow statement",
     "Annual and quarterly cash flow statements, normalised to a consistent schema across issuers.",
     ["symbol", "datatype"], False),
    ("SHARES_OUTSTANDING", "getSharesOutstanding", "Fundamental Data",
     "Shares outstanding",
     "Historical shares-outstanding figures for the specified ticker.",
     ["symbol", "datatype"], False),
    ("EARNINGS", "getEarnings", "Fundamental Data",
     "Earnings history",
     "Annual and quarterly earnings (EPS) history, including reported versus estimated EPS and surprise percentages.",
     ["symbol", "datatype"], False),
    ("EARNINGS_ESTIMATES", "getEarningsEstimates", "Fundamental Data",
     "Analyst earnings estimates",
     "Forward-looking analyst EPS and revenue estimates for the specified ticker.",
     ["symbol", "datatype"], False),
    ("LISTING_STATUS", "getListingStatus", "Fundamental Data",
     "Active and delisted listings",
     "All active or delisted US stocks and ETFs, as of the latest trading day or a specified date in history. Returns CSV.",
     ["datatype"], False),
    ("EARNINGS_CALENDAR", "getEarningsCalendar", "Fundamental Data",
     "Upcoming earnings calendar",
     "Expected earnings dates for companies reporting in the next 3, 6, or 12 months. Returns CSV.",
     ["datatype"], False),
    ("IPO_CALENDAR", "getIpoCalendar", "Fundamental Data",
     "Upcoming IPO calendar",
     "IPOs expected in the next three months. Returns CSV.",
     ["datatype"], False),

    # ---------------- Forex ----------------
    ("CURRENCY_EXCHANGE_RATE", "getCurrencyExchangeRate", "Forex",
     "Realtime exchange rate",
     "Realtime exchange rate for any pair of physical or digital currencies.",
     ["fromCurrency", "toCurrency"], False),
    ("FX_INTRADAY", "getFxIntraday", "Forex",
     "Intraday FX time series",
     "Intraday OHLC candles for the specified currency pair.",
     ["fromSymbol", "toSymbol", "intervalIntraday", "outputsize", "datatype"], True),
    ("FX_DAILY", "getFxDaily", "Forex",
     "Daily FX time series",
     "Daily OHLC candles for the specified currency pair.",
     ["fromSymbol", "toSymbol", "outputsize", "datatype"], False),
    ("FX_WEEKLY", "getFxWeekly", "Forex",
     "Weekly FX time series",
     "Weekly OHLC candles for the specified currency pair.",
     ["fromSymbol", "toSymbol", "datatype"], False),
    ("FX_MONTHLY", "getFxMonthly", "Forex",
     "Monthly FX time series",
     "Monthly OHLC candles for the specified currency pair.",
     ["fromSymbol", "toSymbol", "datatype"], False),

    # ---------------- Crypto ----------------
    ("CRYPTO_INTRADAY", "getCryptoIntraday", "Cryptocurrencies",
     "Intraday crypto time series",
     "Intraday OHLCV candles for the specified digital currency, quoted in the chosen market.",
     ["cryptoSymbol", "market", "intervalIntraday", "outputsize", "datatype"], True),
    ("DIGITAL_CURRENCY_DAILY", "getCryptoDaily", "Cryptocurrencies",
     "Daily crypto time series",
     "Daily OHLCV candles for the specified digital currency, quoted in the chosen market.",
     ["cryptoSymbol", "market", "datatype"], False),
    ("DIGITAL_CURRENCY_WEEKLY", "getCryptoWeekly", "Cryptocurrencies",
     "Weekly crypto time series",
     "Weekly OHLCV candles for the specified digital currency, quoted in the chosen market.",
     ["cryptoSymbol", "market", "datatype"], False),
    ("DIGITAL_CURRENCY_MONTHLY", "getCryptoMonthly", "Cryptocurrencies",
     "Monthly crypto time series",
     "Monthly OHLCV candles for the specified digital currency, quoted in the chosen market.",
     ["cryptoSymbol", "market", "datatype"], False),
]

# Commodities: identical parameter shape, generated from a name table
COMMODITIES = [
    ("WTI", "getWti", "Crude Oil (WTI) prices", "West Texas Intermediate crude oil prices."),
    ("BRENT", "getBrent", "Crude Oil (Brent) prices", "Brent crude oil prices."),
    ("NATURAL_GAS", "getNaturalGas", "Natural gas prices", "Henry Hub natural gas spot prices."),
    ("COPPER", "getCopper", "Copper prices", "Global copper prices."),
    ("ALUMINUM", "getAluminum", "Aluminum prices", "Global aluminum prices."),
    ("WHEAT", "getWheat", "Wheat prices", "Global wheat prices."),
    ("CORN", "getCorn", "Corn prices", "Global corn prices."),
    ("COTTON", "getCotton", "Cotton prices", "Global cotton prices."),
    ("SUGAR", "getSugar", "Sugar prices", "Global sugar prices."),
    ("COFFEE", "getCoffee", "Coffee prices", "Global coffee prices."),
    ("ALL_COMMODITIES", "getAllCommodities", "Global commodities index",
     "Global price index of all commodities."),
]

# Economic indicators: (function, operationId, summary, description, has_interval)
ECONOMIC = [
    ("REAL_GDP", "getRealGdp", "Real GDP", "Annual and quarterly real GDP of the United States.", True),
    ("REAL_GDP_PER_CAPITA", "getRealGdpPerCapita", "Real GDP per capita",
     "Quarterly real GDP per capita of the United States.", False),
    ("TREASURY_YIELD", "getTreasuryYield", "Treasury yield",
     "Daily, weekly, and monthly US Treasury yield for a given constant maturity.", True),
    ("FEDERAL_FUNDS_RATE", "getFederalFundsRate", "Federal funds rate",
     "Daily, weekly, and monthly US federal funds (interest) rate.", True),
    ("CPI", "getCpi", "Consumer Price Index",
     "Monthly and semiannual US Consumer Price Index, a widely used inflation gauge.", True),
    ("INFLATION", "getInflation", "Inflation rate",
     "Annual US inflation rate as measured by consumer prices.", False),
    ("RETAIL_SALES", "getRetailSales", "Retail sales",
     "Monthly US Advance Retail Sales: Retail Trade and Food Services.", False),
    ("DURABLES", "getDurableGoods", "Durable goods orders",
     "Monthly US manufacturers' new orders for durable goods.", False),
    ("UNEMPLOYMENT", "getUnemployment", "Unemployment rate",
     "Monthly US unemployment rate.", False),
    ("NONFARM_PAYROLL", "getNonfarmPayroll", "Nonfarm payroll",
     "Monthly US All Employees: Total Nonfarm figure, commonly known as Total Nonfarm Payroll.", False),
]

# --------------------------------------------------------------------------
# Technical indicators
# (function, extra params beyond symbol/interval/month/datatype, description)
# --------------------------------------------------------------------------

def num(name, desc, default=None, integer=False):
    schema = {"type": "integer", "minimum": 1} if integer else {"type": "number"}
    if default is not None:
        schema["default"] = default
    return {"name": name, "in": "query", "required": False,
            "description": desc, "schema": schema}


MATYPE_DESC = ("Moving average type: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, "
               "5=TRIMA, 6=T3, 7=KAMA, 8=MAMA.")


def matype(name, default=0):
    return {"name": name, "in": "query", "required": False,
            "description": MATYPE_DESC,
            "schema": {"type": "integer", "minimum": 0, "maximum": 8, "default": default}}


MA_LIKE = ["SMA", "EMA", "WMA", "DEMA", "TEMA", "TRIMA", "KAMA", "T3"]

INDICATORS = []

_ma_names = {
    "SMA": "Simple Moving Average", "EMA": "Exponential Moving Average",
    "WMA": "Weighted Moving Average", "DEMA": "Double Exponential Moving Average",
    "TEMA": "Triple Exponential Moving Average", "TRIMA": "Triangular Moving Average",
    "KAMA": "Kaufman Adaptive Moving Average", "T3": "Triple Exponential Moving Average (T3)",
}
for fn in MA_LIKE:
    extra = [{"$ref": "#/components/parameters/timePeriod"},
             {"$ref": "#/components/parameters/seriesType"}]
    INDICATORS.append((fn, _ma_names[fn], extra, True))

INDICATORS += [
    ("VWAP", "Volume Weighted Average Price", [], False),
    ("MAMA", "MESA Adaptive Moving Average",
     [{"$ref": "#/components/parameters/seriesType"},
      num("fastlimit", "Fast limit of the MAMA calculation.", 0.01),
      num("slowlimit", "Slow limit of the MAMA calculation.", 0.01)], True),
    ("MACD", "Moving Average Convergence/Divergence",
     [{"$ref": "#/components/parameters/seriesType"},
      num("fastperiod", "Fast EMA period.", 12, integer=True),
      num("slowperiod", "Slow EMA period.", 26, integer=True),
      num("signalperiod", "Signal line EMA period.", 9, integer=True)], True),
    ("MACDEXT", "MACD with controllable moving average type",
     [{"$ref": "#/components/parameters/seriesType"},
      num("fastperiod", "Fast MA period.", 12, integer=True),
      num("slowperiod", "Slow MA period.", 26, integer=True),
      num("signalperiod", "Signal line MA period.", 9, integer=True),
      matype("fastmatype"), matype("slowmatype"), matype("signalmatype")], True),
    ("STOCH", "Stochastic Oscillator",
     [num("fastkperiod", "Time period of the fast %K line.", 5, integer=True),
      num("slowkperiod", "Time period of the slow %K line.", 3, integer=True),
      num("slowdperiod", "Time period of the slow %D line.", 3, integer=True),
      matype("slowkmatype"), matype("slowdmatype")], True),
    ("STOCHF", "Stochastic Fast",
     [num("fastkperiod", "Time period of the fast %K line.", 5, integer=True),
      num("fastdperiod", "Time period of the fast %D line.", 3, integer=True),
      matype("fastdmatype")], True),
    ("RSI", "Relative Strength Index",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("STOCHRSI", "Stochastic Relative Strength Index",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"},
      num("fastkperiod", "Time period of the fast %K line.", 5, integer=True),
      num("fastdperiod", "Time period of the fast %D line.", 3, integer=True),
      matype("fastdmatype")], True),
    ("WILLR", "Williams %R", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("ADX", "Average Directional Movement Index",
     [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("ADXR", "Average Directional Movement Index Rating",
     [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("APO", "Absolute Price Oscillator",
     [{"$ref": "#/components/parameters/seriesType"},
      num("fastperiod", "Fast MA period.", 12, integer=True),
      num("slowperiod", "Slow MA period.", 26, integer=True),
      matype("matype")], True),
    ("PPO", "Percentage Price Oscillator",
     [{"$ref": "#/components/parameters/seriesType"},
      num("fastperiod", "Fast MA period.", 12, integer=True),
      num("slowperiod", "Slow MA period.", 26, integer=True),
      matype("matype")], True),
    ("MOM", "Momentum",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("BOP", "Balance of Power", [], True),
    ("CCI", "Commodity Channel Index", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("CMO", "Chande Momentum Oscillator",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("ROC", "Rate of Change",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("ROCR", "Rate of Change Ratio",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("AROON", "Aroon", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("AROONOSC", "Aroon Oscillator", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("MFI", "Money Flow Index", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("TRIX", "1-day Rate of Change of a Triple Smooth EMA",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("ULTOSC", "Ultimate Oscillator",
     [num("timeperiod1", "First time period for the indicator.", 7, integer=True),
      num("timeperiod2", "Second time period for the indicator.", 14, integer=True),
      num("timeperiod3", "Third time period for the indicator.", 28, integer=True)], True),
    ("DX", "Directional Movement Index", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("MINUS_DI", "Minus Directional Indicator", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("PLUS_DI", "Plus Directional Indicator", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("MINUS_DM", "Minus Directional Movement", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("PLUS_DM", "Plus Directional Movement", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("BBANDS", "Bollinger Bands",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"},
      num("nbdevup", "Standard deviation multiplier of the upper band.", 2, integer=True),
      num("nbdevdn", "Standard deviation multiplier of the lower band.", 2, integer=True),
      matype("matype")], True),
    ("MIDPOINT", "MidPoint over period",
     [{"$ref": "#/components/parameters/timePeriod"},
      {"$ref": "#/components/parameters/seriesType"}], True),
    ("MIDPRICE", "Midpoint Price over period",
     [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("SAR", "Parabolic SAR",
     [num("acceleration", "Acceleration factor.", 0.01),
      num("maximum", "Acceleration factor maximum value.", 0.20)], True),
    ("TRANGE", "True Range", [], True),
    ("ATR", "Average True Range", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("NATR", "Normalized Average True Range", [{"$ref": "#/components/parameters/timePeriod"}], True),
    ("AD", "Chaikin A/D Line", [], True),
    ("ADOSC", "Chaikin A/D Oscillator",
     [num("fastperiod", "Fast EMA period.", 3, integer=True),
      num("slowperiod", "Slow EMA period.", 10, integer=True)], True),
    ("OBV", "On Balance Volume", [], True),
    ("HT_TRENDLINE", "Hilbert Transform - Instantaneous Trendline",
     [{"$ref": "#/components/parameters/seriesType"}], True),
    ("HT_SINE", "Hilbert Transform - Sine Wave",
     [{"$ref": "#/components/parameters/seriesType"}], True),
    ("HT_TRENDMODE", "Hilbert Transform - Trend vs Cycle Mode",
     [{"$ref": "#/components/parameters/seriesType"}], True),
    ("HT_DCPERIOD", "Hilbert Transform - Dominant Cycle Period",
     [{"$ref": "#/components/parameters/seriesType"}], True),
    ("HT_DCPHASE", "Hilbert Transform - Dominant Cycle Phase",
     [{"$ref": "#/components/parameters/seriesType"}], True),
    ("HT_PHASOR", "Hilbert Transform - Phasor Components",
     [{"$ref": "#/components/parameters/seriesType"}], True),
]

PREMIUM_INDICATORS = {"VWAP", "MACD"}

# --------------------------------------------------------------------------
# Response wiring
# --------------------------------------------------------------------------

def responses(schema_ref="#/components/schemas/GenericPayload", csv=True):
    content = {"application/json": {"schema": {"$ref": schema_ref}}}
    if csv:
        content["text/csv"] = {"schema": {"type": "string"}}
    return OrderedDict([
        ("200", {
            "description": ("Success. Note that Alpha Vantage also returns HTTP 200 for "
                            "rate-limit and validation failures with an explanatory body; "
                            "the APIM outbound policy maps those to 4xx/429."),
            "content": content,
        }),
        ("400", {"description": "Missing or invalid parameter.",
                 "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}}),
        ("401", {"description": "Missing or invalid APIM subscription key."}),
        ("429", {"description": "Rate limit or daily quota exceeded, at the APIM tier or upstream.",
                 "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiError"}}}}),
        ("503", {"description": "Upstream unavailable."}),
    ])


def build_operation(op_id, tag, summary, description, params, premium, deprecated=False):
    desc = description
    if premium:
        desc += ("\n\n> **Entitlement:** requires a premium Alpha Vantage subscription upstream. "
                 "Restrict this operation to an entitled APIM product.")
    op = OrderedDict()
    op["tags"] = [tag]
    op["summary"] = summary
    op["description"] = desc
    op["operationId"] = op_id
    if params:
        op["parameters"] = params
    op["responses"] = responses()
    return {"get": op}


def ref_params(names):
    return [{"$ref": f"#/components/parameters/{n}"} for n in names]


paths = OrderedDict()

for fn, op_id, tag, summary, description, param_names, premium in OPERATIONS:
    paths[f"/{fn}"] = build_operation(
        op_id, tag, summary, description, ref_params(param_names), premium)

for fn, op_id, summary, description in COMMODITIES:
    paths[f"/{fn}"] = build_operation(
        op_id, "Commodities", summary, description,
        ref_params(["commodityInterval", "datatype"]), False)

for fn, op_id, summary, description, has_interval in ECONOMIC:
    names = (["intervalEconomic"] if has_interval else []) + ["datatype"]
    extra = []
    if fn == "TREASURY_YIELD":
        extra = [{"name": "maturity", "in": "query", "required": False,
                  "description": "Constant maturity of the Treasury security.",
                  "schema": {"type": "string",
                             "enum": ["3month", "2year", "5year", "7year", "10year", "30year"],
                             "default": "10year"}}]
    paths[f"/{fn}"] = build_operation(
        op_id, "Economic Indicators", summary, description,
        ref_params(names) + extra, False)

for fn, long_name, extra, supports_month in INDICATORS:
    base = [{"$ref": "#/components/parameters/symbol"},
            {"$ref": "#/components/parameters/intervalIndicator"}]
    if fn == "VWAP":
        base = [{"$ref": "#/components/parameters/symbol"},
                {"$ref": "#/components/parameters/intervalIntraday"}]
    tail = []
    if supports_month:
        tail.append({"$ref": "#/components/parameters/month"})
    tail.append({"$ref": "#/components/parameters/datatype"})
    op_id = "getIndicator" + "".join(p.capitalize() for p in fn.split("_"))
    paths[f"/{fn}"] = build_operation(
        op_id, "Technical Indicators", f"{fn} — {long_name}",
        f"{long_name} values for the specified equity and interval.",
        base + extra + tail, fn in PREMIUM_INDICATORS)

# --------------------------------------------------------------------------
# Assemble the document
# --------------------------------------------------------------------------

spec = OrderedDict()
spec["openapi"] = "3.0.1"
spec["info"] = {
    "title": "Alpha Vantage Market Data API",
    "version": "1.0.0",
    "description": (
        "Facade over the Alpha Vantage market data service, exposed through API Management.\n\n"
        "## How this differs from the vendor API\n\n"
        "Alpha Vantage serves every capability from a single backend route, "
        "`GET https://www.alphavantage.co/query`, discriminated by a `function` query parameter. "
        "OpenAPI cannot model many operations on one path and method, so this specification promotes "
        "each `function` to its own path — `/TIME_SERIES_DAILY`, `/GLOBAL_QUOTE`, and so on. "
        "An API Management policy rewrites the request back to the vendor shape, so path segments "
        "map one-to-one onto the values documented at "
        "https://www.alphavantage.co/documentation/.\n\n"
        "## Authentication\n\n"
        "Callers authenticate to API Management with a subscription key. The upstream `apikey` is held "
        "as a named value in API Management and injected server-side; it is never accepted from, nor "
        "returned to, the caller. Do not send an `apikey` query parameter — it will be overwritten.\n\n"
        "## Error semantics worth knowing\n\n"
        "The vendor returns HTTP 200 for validation failures and throttling alike, carrying an "
        "`Error Message`, `Note`, or `Information` field in the body. The outbound policy inspects "
        "the payload and re-maps these onto 400 and 429 so that standard HTTP client and retry "
        "handling behaves correctly.\n\n"
        "## Entitlements\n\n"
        "Operations marked as requiring a premium subscription will fail against a free upstream key. "
        "Group them into a separate API Management product so entitlement is enforced at the gateway "
        "rather than surfacing as a confusing upstream message.\n\n"
        "## Market data compliance\n\n"
        "Realtime and 15-minute delayed US market data is regulated by the exchanges, FINRA, and the "
        "SEC. Redistribution beyond the licensed scope — including internal onward distribution in "
        "some cases — may require a separate agreement. Confirm the licence terms before making "
        "`entitlement=realtime` operations broadly available."
    ),
    "contact": {"name": "Alpha Vantage documentation",
                "url": "https://www.alphavantage.co/documentation/"},
    "termsOfService": "https://www.alphavantage.co/terms_of_service/",
}
spec["servers"] = [
    {"url": "https://{apimHost}/alphavantage/v1",
     "description": "API Management gateway",
     "variables": {"apimHost": {"default": "apim.example.com",
                                "description": "Your API Management gateway host."}}},
]
spec["security"] = [{"apimSubscriptionKey": []}]
spec["tags"] = [
    {"name": "Core Stock", "description": "Equity, ETF, and mutual fund time series, quotes, and lookup utilities."},
    {"name": "Index Data", "description": "OHLC history for 200+ major market indices."},
    {"name": "Options", "description": "Realtime and historical US options chains."},
    {"name": "Alpha Intelligence", "description": "News sentiment, transcripts, movers, and insider activity."},
    {"name": "Fundamental Data", "description": "Company profiles, financial statements, and corporate actions."},
    {"name": "Forex", "description": "Physical currency exchange rates and FX time series."},
    {"name": "Cryptocurrencies", "description": "Digital currency exchange rates and time series."},
    {"name": "Commodities", "description": "Energy, metals, and agricultural commodity prices."},
    {"name": "Economic Indicators", "description": "US macroeconomic series."},
    {"name": "Technical Indicators", "description": "50+ technical indicators computed on equity price series."},
]
spec["paths"] = paths

spec["components"] = {
    "securitySchemes": {
        "apimSubscriptionKey": {
            "type": "apiKey", "name": "Ocp-Apim-Subscription-Key", "in": "header",
            "description": "API Management subscription key. The upstream vendor key is injected by the gateway.",
        }
    },
    "parameters": COMMON_PARAMS,
    "schemas": {
        "GenericPayload": {
            "type": "object",
            "description": (
                "Vendor payloads are loosely typed: top-level keys vary by function and several "
                "contain spaces and numeric prefixes, for example `Time Series (Daily)` and "
                "`1. open`. The response is passed through unmodified rather than reshaped, so "
                "clients stay compatible with the vendor documentation and with existing "
                "Alpha Vantage client libraries."
            ),
            "additionalProperties": True,
        },
        "ApiError": {
            "type": "object",
            "description": "Normalised error surfaced by the gateway.",
            "properties": {
                "statusCode": {"type": "integer", "example": 429},
                "message": {"type": "string",
                            "example": "Upstream rate limit reached. Retry after the current window closes."},
                "upstream": {"type": "string",
                             "description": "Verbatim explanatory text from the vendor, when present."},
            },
        },
        "GlobalQuote": {
            "type": "object",
            "description": "Illustrative shape of the GLOBAL_QUOTE payload; keys are vendor-defined.",
            "properties": {
                "Global Quote": {
                    "type": "object",
                    "properties": {
                        "01. symbol": {"type": "string", "example": "IBM"},
                        "05. price": {"type": "string", "example": "285.42"},
                        "06. volume": {"type": "string", "example": "3841029"},
                        "07. latest trading day": {"type": "string", "format": "date"},
                        "10. change percent": {"type": "string", "example": "1.2043%"},
                    },
                }
            },
        },
    },
}

# Preserve insertion order in the YAML output
yaml.add_representer(
    OrderedDict,
    lambda dumper, data: dumper.represent_mapping("tag:yaml.org,2002:map", data.items()),
)

with open("/mnt/user-data/outputs/alphavantage-openapi.yaml", "w") as f:
    yaml.dump(spec, f, default_flow_style=False, sort_keys=False,
              allow_unicode=True, width=100)

print(f"operations: {len(paths)}")
by_tag = {}
for p, v in paths.items():
    by_tag.setdefault(v["get"]["tags"][0], []).append(p)
for t, ps in by_tag.items():
    print(f"  {t}: {len(ps)}")
