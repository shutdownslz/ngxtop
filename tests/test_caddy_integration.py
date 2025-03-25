import unittest
import os
import sys
from io import StringIO

from ngxtop import ngxtop
from ngxtop.config_parser import build_pattern


class TestCaddyIntegration(unittest.TestCase):
    """Integration tests for processing Caddy log files."""
    
    def setUp(self):
        # Get the path to the fixture file
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.log_file = os.path.join(self.fixtures_dir, 'caddy_sample.log')
        
        # Skip test if fixture file doesn't exist
        if not os.path.isfile(self.log_file):
            self.skipTest(f"Fixture file not found: {self.log_file}")
            
    def test_caddy_log_integration(self):
        """Test processing a Caddy log file end-to-end"""
        # Create a pattern for Caddy format
        pattern = build_pattern('caddy')
        
        # Open the log file and parse it
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            records = list(ngxtop.parse_log(lines, pattern))
        
        # Verify we processed all 5 records
        self.assertEqual(len(records), 5)
        
        # Check specific records
        status_counts = {200: 0, 201: 0, 204: 0, 404: 0}
        for record in records:
            status_counts[record['status']] += 1
        
        self.assertEqual(status_counts[200], 2)  # Two 200 status codes
        self.assertEqual(status_counts[201], 1)  # One 201 status code
        self.assertEqual(status_counts[204], 1)  # One 204 status code
        self.assertEqual(status_counts[404], 1)  # One 404 status code
        
        # Verify specific fields from a record
        post_record = next(r for r in records if r['request'].startswith('POST'))
        self.assertEqual(post_record['remote_addr'], '203.0.113.15')
        self.assertEqual(post_record['status'], 201)
        self.assertEqual(post_record['body_bytes_sent'], 128)
        self.assertEqual(post_record['request_time'], 0.215643)
        
        # Test derived fields
        not_found_record = next(r for r in records if r['status'] == 404)
        self.assertEqual(not_found_record['status_type'], 4)  # 4xx status
        self.assertIn('/blog/article-not-found', not_found_record['request_path'])
    
    def test_processor_with_caddy_format(self):
        """Test processing Caddy logs through the SQLProcessor"""
        # Create a simple processor for testing
        processor = ngxtop.SQLProcessor(
            [('Test', 'SELECT status, COUNT(*) as count FROM log GROUP BY status')],
            ['status', 'remote_addr', 'request', 'bytes_sent', 'status_type']
        )
        
        # Parse the log file
        pattern = build_pattern('caddy')
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            records = ngxtop.parse_log(lines, pattern)
            
            # Process the records
            processor.process(records)
        
        # Get the report and verify the results
        report = processor.report()
        self.assertIn('running for', report)
        self.assertIn('200', report)
        self.assertIn('404', report)


if __name__ == '__main__':
    unittest.main()