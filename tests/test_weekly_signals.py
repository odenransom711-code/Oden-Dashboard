import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.weekly_signals import (
    normalize_regime,
    infer_expiration_year,
    parse_scan_output,
)


def test_normalize_regime_bull():
    assert normalize_regime('BULL MARKET') == 'BULL'


def test_normalize_regime_bear():
    assert normalize_regime('BEAR MARKET') == 'BEAR'


def test_normalize_regime_neutral_for_anything_else():
    assert normalize_regime('SIDEWAYS / CHOPPY') == 'NEUTRAL'
    assert normalize_regime('') == 'NEUTRAL'


def test_infer_expiration_year_same_year():
    today = date(2026, 7, 8)
    assert infer_expiration_year('Jul 17', today) == '2026-07-17'


def test_infer_expiration_year_wraps_to_next_year():
    today = date(2026, 12, 20)
    assert infer_expiration_year('Jan 15', today) == '2027-01-15'


def test_infer_expiration_year_today_exactly_stays_current_year():
    today = date(2026, 7, 8)
    assert infer_expiration_year('Jul 8', today) == '2026-07-08'


SAMPLE_STDOUT_ONE_SIGNAL = """OPTIONS SIGNALS - CURRENT BEST PLAYS
Date: 2026-07-06 09:03
--- MARKET STATUS ---
SPY: $612.34
vs 200 MA: ABOVE ($580.12)
vs 50 MA:  ABOVE ($605.00)
1-month:   +3.2%
5-day:     +0.8%
REGIME:    BULL MARKET

#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
   Price: $402.10 | Vol: 34%
   Strength: 0.81 | Slope: +18.2
   5d: -1.2% | 20d: +2.1%
"""

SAMPLE_STDOUT_TWO_SIGNALS = """REGIME:    BEAR MARKET

#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
   Price: $402.10 | Vol: 34%
#2 NVDA CALL | Confidence: 68/100 (MED)
   Strike: $140 ATM | Exp: ~Jul 24
   Price: $135.50 | Vol: 41%
"""

SAMPLE_STDOUT_ZERO_SIGNALS = """REGIME:    NEUTRAL
"""

SAMPLE_STDOUT_NO_REGIME = """OPTIONS SIGNALS - CURRENT BEST PLAYS
#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
"""


def test_parse_scan_output_single_signal():
    result = parse_scan_output(SAMPLE_STDOUT_ONE_SIGNAL, today=date(2026, 7, 6))
    assert result['regime'] == 'BULL'
    assert result['signals'] == [
        {
            'rank': 1,
            'ticker': 'HD',
            'direction': 'PUT',
            'confidence': 72,
            'strike': 385,
            'expiration': '2026-07-17',
        }
    ]


def test_parse_scan_output_multiple_signals():
    result = parse_scan_output(SAMPLE_STDOUT_TWO_SIGNALS, today=date(2026, 7, 6))
    assert result['regime'] == 'BEAR'
    assert len(result['signals']) == 2
    assert result['signals'][0]['ticker'] == 'HD'
    assert result['signals'][1] == {
        'rank': 2,
        'ticker': 'NVDA',
        'direction': 'CALL',
        'confidence': 68,
        'strike': 140,
        'expiration': '2026-07-24',
    }


def test_parse_scan_output_zero_signals_is_valid():
    result = parse_scan_output(SAMPLE_STDOUT_ZERO_SIGNALS, today=date(2026, 7, 6))
    assert result['regime'] == 'NEUTRAL'
    assert result['signals'] == []


def test_parse_scan_output_missing_regime_raises():
    try:
        parse_scan_output(SAMPLE_STDOUT_NO_REGIME, today=date(2026, 7, 6))
        assert False, 'expected ValueError'
    except ValueError:
        pass


SAMPLE_STDOUT_SIGNAL_MISSING_STRIKE_LINE = """REGIME:    BULL MARKET

#1 HD PUT | Confidence: 72/100 (HIGH)
#2 NVDA CALL | Confidence: 68/100 (MED)
   Strike: $140 ATM | Exp: ~Jul 24
"""


def test_parse_scan_output_signal_missing_strike_line_does_not_borrow_next_signals_data():
    result = parse_scan_output(
        SAMPLE_STDOUT_SIGNAL_MISSING_STRIKE_LINE, today=date(2026, 7, 6)
    )
    assert result['signals'][0]['ticker'] == 'HD'
    assert result['signals'][0]['strike'] is None
    assert result['signals'][0]['expiration'] is None
    assert result['signals'][1]['ticker'] == 'NVDA'
    assert result['signals'][1]['strike'] == 140
    assert result['signals'][1]['expiration'] == '2026-07-24'
