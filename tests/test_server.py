import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('marketdesk_server', Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patchers=[patch.object(s,'USER_DIR',Path(self.temp.name)),
                       patch.object(s,'DB_FILE',Path(self.temp.name)/'obs.sqlite3'),
                       patch.object(s,'KEY_FILE',Path(self.temp.name)/'key')]
        for p in self.patchers: p.start();self.addCleanup(p.stop)
        s.init_storage()

    def test_symbols_are_validated(self):
        self.assertEqual(s.valid_symbol(' aapl '),'AAPL')
        for val in ('AAPL?token=stolen','../../passwd','AAPL/US','', 'x'*50):
            with self.assertRaises(ValueError):s.valid_symbol(val)

    def test_token_uses_private_file(self):
        s.save_key('abc12345678901234567')
        self.assertEqual(s.get_key(),'abc12345678901234567')
        self.assertEqual(s.KEY_FILE.stat().st_mode & 0o777, 0o600)

    def test_no_synthetic_prices_in_quote(self):
        with patch.object(s,'provider_get',return_value=({'c':0,'t':0},False)):
            data=s.handle_api('/api/quote',{'symbol':['AAPL']})
        self.assertEqual(data['items'][0]['status'],'unavailable')
        self.assertIsNone(data['items'][0]['quote'])

    def test_store_only_realistic_observations(self):
        t=1762080000000
        self.assertTrue(s.store_point('AAPL',t,210.4,'finnhub_quote'))
        self.assertFalse(s.store_point('AAPL',t,0,'finnhub_quote'))
        self.assertFalse(s.store_point('AAPL',t,-10,'finnhub_quote'))
        self.assertEqual(s.get_history('AAPL')[0]['p'],210.4)

    def test_candle_403_becomes_transparent_unavailable(self):
        with patch.object(s,'provider_get',side_effect=s.ProviderError(403,'Premium endpoint')):
            result=s.handle_api('/api/candles',{'symbol':['AAPL'],'resolution':['D'],
                'from':['1730000000'],'to':['1762000000']})
        self.assertEqual(result['status'],'entitlement')
        self.assertIsNone(result['candles'])

    def test_quote_save_provider_timestamp(self):
        with patch.object(s,'provider_get',return_value=({'c':123.45,'t':1762080000,'dp':1.5,'pc':121.2},False)):
            data=s.handle_api('/api/quote',{'symbol':['AAPL']})
        self.assertEqual(data['items'][0]['status'],'ok')
        self.assertEqual(s.get_history('AAPL')[0]['t'],1762080000000)

    def test_finnhub_search_uses_real_provider_results(self):
        observed={'result':[{'symbol':'TSLA','description':'Tesla Inc'},
                            {'symbol':'TEST','description':'Test Company'}]}
        with patch.object(s,'provider_get',return_value=(observed,False)) as provider:
            result=s.handle_api('/api/search',{'q':['Tes']})
        self.assertEqual(result,observed)
        self.assertEqual(provider.call_args.args,('search',{'q':'Tes'}))
        self.assertEqual(provider.call_args.kwargs['ttl'],900)

    def test_empty_search_does_not_contact_provider(self):
        with patch.object(s,'provider_get') as provider:
            result=s.handle_api('/api/search',{'q':['   ']})
        self.assertEqual(result,{'result':[]})
        provider.assert_not_called()

    def test_history_requires_valid_symbol(self):
        with self.assertRaises(ValueError):s.handle_api('/api/history',{'symbol':['../etc']})



class ConnectionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        ServerTests.setUp(self)

    def test_certificate_error_is_explained(self):
        import ssl, urllib.error
        error = urllib.error.URLError(ssl.SSLCertVerificationError('certificate verify failed'))
        kind, message = s.classify_network_error(error)
        self.assertEqual(kind, 'tls_certificate')
        self.assertIn('certificate verification', message)

    def test_dns_error_is_explained(self):
        import socket, urllib.error
        kind, message = s.classify_network_error(urllib.error.URLError(socket.gaierror(8, 'not known')))
        self.assertEqual(kind, 'dns')
        self.assertIn('DNS', message)

    def test_timeout_error_is_explained(self):
        import urllib.error
        kind, message = s.classify_network_error(urllib.error.URLError(TimeoutError('timed out')))
        self.assertEqual(kind, 'timeout')
        self.assertIn('timed out', message)

    def test_probe_no_token(self):
        result=s.handle_api('/api/diagnose',{})
        self.assertFalse(result['ok'])
        self.assertEqual(result['kind'], 'no_token')
        self.assertFalse(result['live_trade_verified'])
        self.assertNotIn('token',str(result.get('tls_trust','')).lower())

    def test_probe_success_is_snapshot_not_trade(self):
        s.save_key('token1234567890')
        data={'c':230.4,'t':1762080000,'pc':230.0}
        with patch.object(s,'provider_get',return_value=(data,False)) as provider:
            result=s.handle_api('/api/diagnose',{})
        self.assertTrue(result['ok'])
        self.assertEqual(result['kind'],'quote_received')
        self.assertFalse(result['live_trade_verified'])
        self.assertEqual(result['quote_time_ms'],1762080000000)
        self.assertTrue(provider.call_args.kwargs['bypass_cache'])

    def test_probe_distinguishes_network_errors(self):
        s.save_key('token1234567890')
        with patch.object(s,'provider_get',side_effect=s.ProviderError(502,'DNS unavailable',kind='dns')):
            result=s.handle_api('/api/diagnose',{})
        self.assertFalse(result['ok'])
        self.assertEqual(result['kind'],'dns')
        self.assertIn('DNS',result['message'])

    def test_request_keeps_certificate_validation_enabled(self):
        from unittest.mock import MagicMock
        s.save_key('token1234567890')
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'{"c": 230.4, "t": 1762080000}'
        with patch.object(s.urllib.request,'urlopen',return_value=response) as urlopen:
            result,_=s.provider_get('quote',{'symbol':'AAPL'},ttl=0)
        self.assertEqual(result['c'],230.4)
        ctx=urlopen.call_args.kwargs['context']
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode,s.ssl.CERT_REQUIRED)

    def test_provider_categorizes_401_without_leaking_token(self):
        import urllib.error
        s.save_key('thisIsMyPrivateToken123')
        error=urllib.error.HTTPError('https://finnhub.io/api/v1/quote',401,'Unauthorized',{},None)
        with patch.object(s.urllib.request,'urlopen',side_effect=error):
            with self.assertRaises(s.ProviderError) as context:
                s.provider_get('quote',{'symbol':'AAPL'},ttl=0)
        self.assertEqual(context.exception.kind,'authentication')
        self.assertNotIn('thisIsMyPrivateToken123',context.exception.message)

    def test_provider_converts_ssl_error(self):
        import ssl, urllib.error
        s.save_key('somePrivateToken123')
        error=urllib.error.URLError(ssl.SSLCertVerificationError('certificate verify failed'))
        with patch.object(s.urllib.request,'urlopen',side_effect=error):
            with self.assertRaises(s.ProviderError) as context:
                s.provider_get('quote',{'symbol':'AAPL'},ttl=0)
        self.assertEqual(context.exception.kind,'tls_certificate')
        self.assertNotIn('somePrivateToken123',context.exception.message)

    def test_network_failure_uses_brief_cooldown_not_fake_quotes(self):
        import urllib.error, socket
        s.save_key('somePrivateToken123')
        with patch.object(s.urllib.request,'urlopen',side_effect=urllib.error.URLError(socket.gaierror(8,'DNS failure'))):
            result=s.handle_api('/api/quotes',{'symbols':['AAPL,NVDA,MSFT']})
        self.assertEqual(len(result['items']),3)
        self.assertEqual([x['status'] for x in result['items']],['error','skipped','skipped'])
        self.assertEqual(result['items'][0]['status'],'error')
        self.assertEqual(result['items'][0]['code'],502)
        self.assertIsNone(result['items'][0]['quote'])
        with self.assertRaises(s.ProviderError) as exc:
            s.provider_get('quote',{'symbol':'AAPL'})
        self.assertEqual(exc.exception.kind,'network_cooldown')

    def test_live_check_bypasses_network_cooldown_but_not_tls(self):
        s.save_key('somePrivateToken123')
        s.NETWORK_BACKOFF_UNTIL=s.time.monotonic()+50
        try:
            with patch.object(s,'provider_get',return_value=({'c':12.3,'t':1762080000},False)) as fake:
                result=s.diagnose_finnhub()
            self.assertTrue(result['ok'])
            self.assertTrue(fake.call_args.kwargs['bypass_cache'])
        finally:
            s.NETWORK_BACKOFF_UNTIL=0.0

    def test_mac_keychain_fallback_stays_secure(self):
        from unittest.mock import MagicMock
        with patch.object(s.sys,'platform','darwin'), patch.object(s.subprocess,'run',side_effect=FileNotFoundError('security missing')):
            s.verified_tls_context.cache_clear()
            ctx, source=s.verified_tls_context()
        s.verified_tls_context.cache_clear()
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode,s.ssl.CERT_REQUIRED)
        self.assertIn('unavailable', source)

if __name__=='__main__':unittest.main()
