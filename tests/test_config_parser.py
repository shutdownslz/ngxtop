import unittest
from ngxtop import config_parser


class TestConfigParser(unittest.TestCase):

    def test_get_log_formats(self):
        config = '''
            http {
                # ubuntu default, log_format on multiple lines
                log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                                  "$status $body_bytes_sent '$http_referer' "
                                  '"$http_user_agent" "$http_x_forwarded_for"';
                # name can also be quoted, and format don't always have to
                log_format  'te st'  $remote_addr;
            }
        '''
        formats = dict(config_parser.get_log_formats(config))
        self.assertIn('main', formats)
        self.assertIn("'$http_referer'", formats['main'])
        self.assertIn('te st', formats)

    def test_get_access_logs_no_format(self):
        config = '''
                http {
                    # ubuntu default
                    access_log /var/log/nginx/access.log;
                    # syslog is a valid access log, but we can't follow it
                    access_log syslog:server=address combined;
                    # commented
                    # access_log commented;
                    server {
                        location / {
                            # has parameter with default format
                            access_log /path/to/log gzip=1;
                        }
                    }
                }
            '''
        logs = dict(config_parser.get_access_logs(config))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs['/var/log/nginx/access.log'], 'combined')
        self.assertEqual(logs['/path/to/log'], 'combined')

    def test_access_logs_with_format_name(self):
        config = '''
                http {
                    access_log /path/to/main.log main gzip=5 buffer=32k flush=1m;
                    server {
                        access_log /path/to/test.log 'te st';
                    }
                }
            '''
        logs = dict(config_parser.get_access_logs(config))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs['/path/to/main.log'], 'main')
        self.assertEqual(logs['/path/to/test.log'], 'te st')

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
            'http_referer', 'http_user_agent', 'request_time', 'request_path',
            'host'
        ]

        for field in expected_fields:
            self.assertIn(field, variables)


if __name__ == '__main__':
    unittest.main()
