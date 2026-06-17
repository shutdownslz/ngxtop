import os
import unittest

from ngxtop import ngxtop
from ngxtop.config_parser import build_pattern


class TestJsonFormat(unittest.TestCase):
    """Tests for the generic flat-JSON log format (-f json)."""

    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.log_file = os.path.join(self.fixtures_dir, 'json_sample.log')
        if not os.path.isfile(self.log_file):
            self.skipTest("Fixture file not found: %s" % self.log_file)
        with open(self.log_file, 'r') as f:
            self.lines = f.readlines()

    def _records(self):
        pattern = build_pattern('json')
        return list(ngxtop.parse_log(self.lines, pattern))

    def test_build_pattern_returns_sentinel(self):
        self.assertEqual(build_pattern('json'), 'json')

    def test_bad_lines_are_skipped(self):
        # 5 valid JSON objects; 1 non-JSON line and 1 truncated JSON are skipped
        records = self._records()
        self.assertEqual(len(records), 5)

    def test_status_type_derived(self):
        by_status = {r['status']: r for r in self._records()}
        self.assertEqual(by_status[200]['status_type'], 2)
        self.assertEqual(by_status[301]['status_type'], 3)
        self.assertEqual(by_status[404]['status_type'], 4)
        self.assertEqual(by_status[500]['status_type'], 5)

    def test_request_path_strips_query(self):
        rec = next(r for r in self._records() if r['status'] == 301)
        self.assertEqual(rec['request_path'], '/login')
        paged = next(r for r in self._records() if r.get('req_uri') == '/api/users?page=1')
        self.assertEqual(paged['request_path'], '/api/users')

    def test_request_line_built_from_method_and_uri(self):
        rec = next(r for r in self._records() if r['status'] == 404)
        self.assertEqual(rec['request'], 'POST /api/orders')

    def test_aliases_for_bytes_and_time(self):
        rec = next(r for r in self._records() if r['status'] == 404)
        self.assertEqual(rec['bytes_sent'], 1024)
        self.assertAlmostEqual(rec['request_time'], 0.331)

    def test_arbitrary_fields_passed_through(self):
        rec = self._records()[0]
        # original keys must survive so they can be used in --group-by / --filter
        self.assertEqual(rec['domain'], 'example.test')
        self.assertEqual(rec['auth_user'], 'alice')
        self.assertEqual(rec['upstream_status'], '200')

    def test_status_coerced_to_int(self):
        for rec in self._records():
            self.assertIsInstance(rec['status'], int)

    def test_end_to_end_through_processor(self):
        processor = ngxtop.SQLProcessor(
            [('by_status_type', "SELECT status_type, COUNT(*) AS count FROM log GROUP BY status_type")],
            ['status', 'status_type', 'bytes_sent', 'request_path', 'domain'],
        )
        processor.process(self._records())
        report = processor.report()
        self.assertIn('running for', report)
        self.assertEqual(processor.count(), 5)


if __name__ == '__main__':
    unittest.main()
