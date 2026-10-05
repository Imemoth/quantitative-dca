"""Pure trailing calculations on an already aligned, economic OHLC series.

Missing sessions must be represented by None, never removed. Sample standard
deviations use ddof=1; slope scale is OLS residual RMSE (n denominator).
Zero denominators/scales are missing. No clipping or fitted transforms occur.
"""
import math
import statistics


def _window(series, n, *, allow_zero=False):
    xs = list(series)[-n:]
    if len(xs) != n or any(x is None or not math.isfinite(x) or x < 0 or (x == 0 and not allow_zero) for x in xs):
        return None
    return xs


def trailing_return(prices, sessions):
    if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions < 1:
        raise ValueError("sessions must be a positive integer")
    xs = _window(prices, sessions+1)
    return None if xs is None else xs[-1]/xs[0]-1


def compute_trailing_features(close, high, low, usd_turnover):
    """Return exactly the Task 2 V1 signals; callers own PIT ingress."""
    close, high, low, usd_turnover = map(list, (close, high, low, usd_turnover))
    if len({len(x) for x in (close, high, low, usd_turnover)}) != 1:
        raise ValueError("unaligned series")
    out = {f"return_{n}d_raw": trailing_return(close,n) for n in (5,20,60,120,252)}
    for n in (20,50,200):
        xs = _window(close,n)
        out[f"distance_ma{n}_raw"] = None if xs is None else xs[-1]/statistics.mean(xs)-1
    xs = _window(close,252)
    out["distance_52week_high_raw"] = None if xs is None else xs[-1]/max(xs)-1
    for n in (20,60):
        xs = _window(close,n)
        slope = None
        if xs is not None:
            ys = [math.log(x) for x in xs]
            center = (n-1)/2
            mean = statistics.mean(ys)
            beta = sum((i-center)*(y-mean) for i,y in enumerate(ys))/sum((i-center)**2 for i in range(n))
            scale = math.sqrt(sum((y-mean-beta*(i-center))**2 for i,y in enumerate(ys))/n)
            if scale > 1e-14:
                slope = beta/scale
        out[f"trend_slope_{n}d_normalized"] = slope
    for n in (20,60):
        xs = _window(close,n+1)
        returns = None if xs is None else [math.log(b/a) for a,b in zip(xs,xs[1:])]
        out[f"realized_volatility_{n}d_raw"] = None if returns is None else statistics.stdev(returns)*math.sqrt(252)
        if n == 60:
            out["downside_volatility_60d_raw"] = None if returns is None else statistics.stdev([min(r,0) for r in returns])*math.sqrt(252)
    numerator, denominator = [out[f"realized_volatility_{n}d_raw"] for n in (20,60)]
    out["volatility_ratio_20d_60d_raw"] = None if numerator is None or not denominator else numerator/denominator
    cs, hs, ls = _window(close,21), _window(high,20), _window(low,20)
    out["atr_20d_percent_price_raw"] = None if any(x is None for x in (cs,hs,ls)) else statistics.mean(max(h-l,abs(h-p),abs(l-p)) for h,l,p in zip(hs,ls,cs[:-1]))/cs[-1]
    xs = _window(close,253)
    out["current_drawdown_raw"] = None if xs is None else xs[-1]/max(xs[-252:])-1
    for n in (60,252):
        xs = _window(close,n)
        value = None
        if xs is not None:
            peak, value = xs[0], 0.
            for p in xs:
                peak = max(peak,p)
                value = min(value,p/peak-1)
        out[f"maximum_drawdown_{n}d_raw"] = value
    xs = _window(close,252)
    out["drawdown_duration_sessions_raw"] = None if xs is None else 251-max(i for i,p in enumerate(xs) if p == max(xs))
    dv = _window(usd_turnover,20,allow_zero=True)
    out["median_dollar_volume_20d_log"] = None if dv is None else math.log1p(statistics.median(dv))
    xs = _window(close,21)
    dv = _window(usd_turnover,20)
    out["amihud_illiquidity_20d_log"] = None if xs is None or dv is None else math.log1p(statistics.mean(abs(b/a-1)/v for a,b,v in zip(xs,xs[1:],dv)))
    return out
