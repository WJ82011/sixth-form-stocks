"""Coinbase provider boundaries and separate offline cache with fixture data."""
import contextlib
import datetime as dt
import urllib.error
import unittest
from unittest.mock import patch

import crypto38 as crypto
import test_v3_api as fixture

s = fixture.s


class CryptoTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_supported_markets_and_rejected_identifiers(self):
        expected = {
            'BTC-USD': 'BTC', 'ETH-USD': 'ETH', 'SOL-USD': 'SOL', 'XRP-USD': 'XRP',
            'DOGE-USD': 'DOGE', 'ADA-USD': 'ADA', 'LINK-USD': 'LINK',
            'AVAX-USD': 'AVAX', 'LTC-USD': 'LTC',
        }
        for product, base in expected.items():
            self.assertEqual(crypto.MARKETS[product]['base'], base)
            self.assertEqual(crypto.MARKETS[product]['quote'], 'USD')
            self.assertEqual(crypto.MARKETS[product]['providerName'], product)
        self.assertEqual(crypto.UNAVAILABLE, [])
        for symbol in ('BTC', 'AAPL', '../ETH-USD', 'BTC-USDT', 'SHIB-USD'):
            with self.assertRaises(ValueError):
                crypto.packet(vars(s), symbol, 'quote')

    def test_completed_candle_bounds_and_missing_interval(self):
        rows = [[240, 10, 12, 11, 12, 1], [60, 10, 12, 11, 11, 1],
                [180, 10, 12, 11, 12, 1], [120, 10, 12, 11, 13, 1]]
        self.assertEqual(crypto.normalise_candles(rows, 60, 240, 60),
                         [{'t': 120000, 'p': 11}, {'t': 240000, 'p': 12}])

    def test_quote_cache_survives_a_provider_outage(self):
        now = int(s.time.time())
        ticker = {'price': '101.5', 'time': crypto.iso(now)}
        with patch.dict(crypto.RETRY_AFTER, clear=True), patch.object(crypto, 'public_get', return_value=ticker):
            first = crypto.packet(vars(s), 'BTC-USD', 'quote')
            self.assertEqual(first['price'], 101.5)
            with patch.object(s.time, 'time', return_value=now+30), patch.object(
                    crypto, 'public_get', side_effect=urllib.error.URLError('offline')):
                second = crypto.packet(vars(s), 'BTC-USD', 'quote')
            self.assertEqual(second['status'], 'saved')
            self.assertEqual(first['time'], second['time'])

    def test_year_is_paginated_and_does_not_admit_the_open_candle(self):
        def candles(g, product, path, params):
            self.assertEqual((product, path), ('ETH-USD', 'candles'))
            left = int(dt.datetime.fromisoformat(params['start']).timestamp())
            right = int(dt.datetime.fromisoformat(params['end']).timestamp())
            step = params['granularity']
            self.assertLessEqual((right-left)//step, 290)
            return [[t, 100, 101, 100, 101, 2] for t in range(left,right+1,step)]
        with patch.object(crypto, 'public_get', side_effect=candles) as provider:
            packet = crypto.fetch_chart(vars(s), 'ETH-USD', '1Y', 1794225599000)
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(len(packet['points']), 365)
        self.assertEqual(packet['points'][-1]['t'], packet['end'])

    def test_utc_boundary_is_not_an_equity_session(self):
        import events42
        saturday = dt.datetime(2026, 11, 14, 1, tzinfo=dt.timezone.utc)
        friday = dt.datetime(2026, 11, 13, 23, tzinfo=dt.timezone.utc)
        points = [{'t': int(friday.timestamp()*1000), 'p': 100}, {'t': int(saturday.timestamp()*1000), 'p': 110}]
        change = crypto.utc_change(points)
        self.assertEqual(change['timezone'], 'UTC')
        self.assertAlmostEqual(change['changePct'], 10)
        self.assertTrue(change['end'].startswith('2026-11-14'))
        self.assertFalse(events42.is_session(saturday.date()))
        self.assertAlmostEqual(crypto.match_move(points, 5)['changePct'], 10)
        self.assertIsNone(crypto.match_move([{'t': 1, 'p': 100}, {'t': 2, 'p': 104}], 5))
        self.assertTrue(events42.is_session(friday.date()))

    def test_followed_markets_are_collected_first(self):
        crypto.follow(vars(s), ['SOL-USD', 'NOPE', 'SOL-USD'], 10)
        order = crypto.rotation(vars(s))
        self.assertEqual(order[0], 'SOL-USD')
        self.assertEqual(order.count('SOL-USD'), 1)
        self.assertIn('BTC-USD', order)

    def test_the_same_coinbase_trade_does_not_alert_twice(self):
        now = int(s.time.time())
        with patch.object(s.time, 'time', return_value=now):
            s.change_alerts({'action': 'create', 'symbol': 'SOL-USD', 'direction': 'above', 'target': 100, 'unit': 'USD'})
        ticker = {'price': '150', 'time': crypto.iso(now+2)}
        with patch.dict(crypto.RETRY_AFTER, clear=True), patch.object(crypto, 'public_get', return_value=ticker):
            with patch.object(s.time, 'time', return_value=now+2):
                crypto.packet(vars(s), 'SOL-USD', 'quote')
            with patch.object(s.time, 'time', return_value=now+40):
                crypto.packet(vars(s), 'SOL-USD', 'quote')
        with contextlib.closing(s.db_connection()) as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM price_alert_events').fetchone()[0], 1)
