import unittest
from ngxtop import config_parser


class TestConfigParser(unittest.TestCase):
    """Unit tests for config_parser module, focusing on Caddy format."""
    
    def test_build_pattern_caddy_format(self):
        """Test that build_pattern correctly handles the 'caddy' format."""
        pattern = config_parser.build_pattern('caddy')
        self.assertEqual(pattern, 'caddy')  # For caddy, we return the string 'caddy' not a regex pattern
    
    def test_extract_variables_caddy_format(self):
        """Test that extract_variables returns the expected fields for caddy format."""
        variables = list(config_parser.extract_variables('caddy'))
        
        # Check that all expected fields are present
        expected_fields = [
            'remote_addr', 'status', 'request', 'body_bytes_sent', 
            'http_referer', 'http_user_agent', 'request_time', 'request_path'
        ]
        
        for field in expected_fields:
            self.assertIn(field, variables)


if __name__ == '__main__':
    unittest.main()
