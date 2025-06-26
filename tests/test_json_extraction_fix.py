import unittest
import logging
from io import StringIO
from ngxtop import ngxtop


class TestJsonExtractionFix(unittest.TestCase):
    """Test the JSON extraction fix for cases with { in header values."""
    
    def test_json_extraction_with_brace_in_headers(self):
        """Test extraction when { appears in headers before the actual JSON."""
        # Simulate a log line where { appears in a header value
        lines = [
            '2025/06/26 07:07:38.123 INFO http.log.access.log2 handled request {"request": {"headers": {"User-Agent": ["Mozilla {test}"]}, "remote_ip": "127.0.0.1"}, "status": 200}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should successfully parse
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['remote_addr'], '127.0.0.1')
        self.assertEqual(records[0]['status'], 200)
    
    def test_json_extraction_without_handled_request(self):
        """Test extraction for pure JSON lines without the prefix."""
        lines = [
            '{"request": {"remote_ip": "192.168.1.1", "method": "GET", "uri": "/test"}, "status": 200, "size": 1000}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should successfully parse
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['remote_addr'], '192.168.1.1')
        self.assertEqual(records[0]['status'], 200)
    
    def test_complex_caddy_log_line(self):
        """Test a complex real-world Caddy log line."""
        # Using a line similar to the problematic one from production
        lines = [
            '2025/06/26 07:07:38.690 INFO    http.log.access.log10   handled request {"request": {"remote_ip": "71.47.115.218", "headers": {"Sec-Ch-Ua": ["\\"Not {A;Brand}\\";v=\\"24\\""], "User-Agent": ["Mozilla/5.0"]}, "uri": "/test"}, "status": 200, "size": 47875}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should successfully parse despite { in header value
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['remote_addr'], '71.47.115.218')
        self.assertEqual(records[0]['status'], 200)
        self.assertEqual(records[0]['body_bytes_sent'], 47875)


if __name__ == '__main__':
    unittest.main()