import unittest
import logging
from io import StringIO
from ngxtop import ngxtop


class TestDebugJsonParsing(unittest.TestCase):
    """Test the enhanced debugging for JSON parsing errors."""
    
    def setUp(self):
        """Set up logging capture."""
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.WARNING)
        
        # Get the logger used by ngxtop
        self.logger = logging.getLogger()
        self.logger.addHandler(self.handler)
        self.original_level = self.logger.level
        self.logger.setLevel(logging.WARNING)
    
    def tearDown(self):
        """Clean up logging."""
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.original_level)
        self.log_capture.close()
    
    def test_extra_data_json_error(self):
        """Test handling of JSON with extra data."""
        # Simulate a log line with multiple JSON objects concatenated
        lines = [
            '2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {"request": {"remote_ip": "127.0.0.1"}, "status": 200}{"extra": "data"}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should fail to parse due to extra data
        self.assertEqual(len(records), 0)
        
        # Check that concise warning was logged
        log_output = self.log_capture.getvalue()
        self.assertIn("Error parsing log line:", log_output)
        self.assertIn("Extra data:", log_output)
        
        # Detailed debugging should NOT be present (we're at WARNING level)
        self.assertNotIn("Detailed JSON parsing error:", log_output)
        self.assertNotIn("Complete line", log_output)
        self.assertNotIn("Extracted JSON string", log_output)
    
    def test_truncated_json_error(self):
        """Test handling of truncated JSON."""
        lines = [
            '2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {"request": {"remote_ip": "127.0.0.1", "method": "GET"'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should skip due to missing closing brace
        self.assertEqual(len(records), 0)
    
    def test_malformed_json_with_debug(self):
        """Test detailed debugging output for malformed JSON."""
        # JSON with syntax error
        lines = [
            '2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {"request": {"remote_ip": "127.0.0.1",, "status": 200}}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should fail to parse
        self.assertEqual(len(records), 0)
        
        # Check that only concise output is present (no verbose details)
        log_output = self.log_capture.getvalue()
        self.assertIn("Error parsing log line:", log_output)
        self.assertNotIn("Detailed JSON parsing error:", log_output)
    
    def test_extra_data_json_error_verbose(self):
        """Test verbose mode shows detailed debugging info."""
        # Enable INFO level logging to simulate verbose mode
        self.logger.setLevel(logging.INFO)
        self.handler.setLevel(logging.INFO)
        
        # Simulate a log line with multiple JSON objects concatenated
        lines = [
            '2025/03/25 11:30:51.092 INFO http.log.access.log2 handled request {"request": {"remote_ip": "127.0.0.1"}, "status": 200}{"extra": "data"}'
        ]
        
        records = list(ngxtop.parse_log(lines, 'caddy'))
        
        # Should fail to parse due to extra data
        self.assertEqual(len(records), 0)
        
        # Check that detailed debugging IS present in verbose mode
        log_output = self.log_capture.getvalue()
        self.assertIn("Error parsing log line:", log_output)  # WARNING level message
        self.assertIn("Detailed JSON parsing error:", log_output)  # INFO level message
        self.assertIn("Error position:", log_output)
        self.assertIn("Complete line", log_output)
        self.assertIn("Extracted JSON string", log_output)
        self.assertIn("="*80, log_output)


if __name__ == '__main__':
    unittest.main()