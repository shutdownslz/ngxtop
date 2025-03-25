import unittest
import re
import json
from io import StringIO
from ngxtop import ngxtop

# Sample log lines
NGINX_COMBINED_LOG = '192.168.1.1 - - [25/Mar/2025:11:30:51 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"'
CADDY_JSON_LOG = '''2025/03/25 11:30:51.092 INFO    http.log.access.log2    handled request {"request": {"remote_ip": "66.249.79.162", "remote_port": "51574", "client_ip": "66.249.79.162", "proto": "HTTP/2.0", "method": "GET", "host": "example.com", "uri": "/index.html", "headers": {"Accept-Encoding": ["gzip, deflate, br"], "Cookie": ["REDACTED"], "Accept": ["text/html,application/xhtml+xml,application/signed-exchange;v=b3,application/xml;q=0.9,*/*;q=0.8"], "From": ["googlebot(at)googlebot.com"], "User-Agent": ["Mozilla/5.0 (Linux; Android 6.0.1)"]}}, "bytes_read": 0, "user_id": "", "duration": 4.116943506, "size": 16818, "status": 200}'''


class TestParseLog(unittest.TestCase):
    """Test the log parsing functionality for Caddy format."""
    
    def test_parse_caddy_log(self):
        """Test parsing of Caddy JSON log format"""
        lines = [CADDY_JSON_LOG]
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        self.assertEqual(len(records), 1)
        record = records[0]
        
        self.assertEqual(record['remote_addr'], '66.249.79.162')
        self.assertEqual(record['status'], 200)
        self.assertEqual(record['body_bytes_sent'], 16818)
        self.assertEqual(record['bytes_sent'], 16818)
        self.assertEqual(record['request_time'], 4.116943506)
        self.assertEqual(record['request'], 'GET /index.html HTTP/1.1')
        self.assertEqual(record['status_type'], 2)  # 2xx status
        self.assertEqual(record['request_path'], '/index.html')
    
    def test_parse_caddy_log_invalid_json(self):
        """Test handling of invalid JSON in Caddy logs"""
        lines = ['Invalid JSON data', '{ "incomplete": "json"']
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should skip invalid lines
        self.assertEqual(len(records), 0)
    
    def test_parse_caddy_log_missing_fields(self):
        """Test handling of Caddy logs with missing fields"""
        # Missing status field
        log_missing_status = json.dumps({"request": {"remote_ip": "127.0.0.1", "method": "GET", "uri": "/test"}})
        # Missing request field
        log_missing_request = json.dumps({"status": 404, "size": 123})
        
        lines = [
            f'2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {log_missing_status}',
            f'2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {log_missing_request}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should handle the log with missing status
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['remote_addr'], '127.0.0.1')
        self.assertEqual(records[0]['status'], 0)  # Default value when missing


if __name__ == '__main__':
    unittest.main()