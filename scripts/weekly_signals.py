"""
Weekly stock-signals scan: clones adv-andrew/mcmc-cuda-model, runs its
options scanner, parses the console output, and pushes the result to
Supabase as the Finance page's `stockpicks` data.

Usage:
    python3 weekly_signals.py [--dry-run]
"""
import re
from datetime import date


REGIME_RE = re.compile(r'^REGIME:\s*(.+)$', re.MULTILINE)
SIGNAL_HEADER_RE = re.compile(
    r'^#(\d+)\s+(\S+)\s+(CALL|PUT)\s+\|\s+Confidence:\s+(\d+)/100',
    re.MULTILINE,
)
STRIKE_EXP_RE = re.compile(r'Strike:\s*\$(\d+)\s+ATM\s+\|\s+Exp:\s*~(\w{3}\s+\d+)')


def normalize_regime(raw):
    """Normalize a raw REGIME line's captured text to BULL/BEAR/NEUTRAL."""
    text = (raw or '').upper()
    if 'BULL' in text:
        return 'BULL'
    if 'BEAR' in text:
        return 'BEAR'
    return 'NEUTRAL'


def infer_expiration_year(month_day, today):
    """Given a 'Mon DD' string with no year, infer YYYY-MM-DD using `today`
    as the reference point. Option expirations are always in the future,
    so if the current-year interpretation is already in the past, it must
    mean next year's occurrence of that month/day instead."""
    from datetime import datetime as _dt
    parsed = _dt.strptime(month_day.strip(), '%b %d')
    candidate = date(today.year, parsed.month, parsed.day)
    if candidate < today:
        candidate = date(today.year + 1, parsed.month, parsed.day)
    return candidate.isoformat()


def parse_scan_output(stdout, today=None):
    """Parse options_now.py's stdout into {"regime": str, "signals": [...]}.
    Raises ValueError if no REGIME line is found."""
    if today is None:
        today = date.today()

    regime_match = REGIME_RE.search(stdout)
    if not regime_match:
        raise ValueError('No REGIME line found in scan output')
    regime = normalize_regime(regime_match.group(1))

    signals = []
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        header = SIGNAL_HEADER_RE.match(line)
        if not header:
            continue
        rank, ticker, direction, confidence = header.groups()
        strike = None
        expiration = None
        for lookahead in lines[i + 1:i + 3]:
            if SIGNAL_HEADER_RE.match(lookahead):
                break
            se = STRIKE_EXP_RE.search(lookahead)
            if se:
                strike = int(se.group(1))
                expiration = infer_expiration_year(se.group(2), today)
                break
        signals.append({
            'rank': int(rank),
            'ticker': ticker,
            'direction': direction,
            'confidence': int(confidence),
            'strike': strike,
            'expiration': expiration,
        })
    return {'regime': regime, 'signals': signals}
