"""Coinbase provider boundaries and separate offline cache with fixture data."""
import datetime as dt
import urllib.error
import unittest
from unittest.mock import patch

import crypto38 as crypto
import test_v3_api as fixture

s = fixture.s


class CryptoTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_only_the_two_supported_spot_markets_are_allowed(self):
        for symbol in ('BTC', 'AAPL', '../ETH-USD', 'BTC-USDT'):
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
