import os
import unittest

from ngxtop import ngxtop
from ngxtop.config_parser import build_pattern


def _query_args(queries):
    """Build a docopt-style arguments dict for the `query` subcommand."""
    return {
        '<var>': [],
        'print': False, 'top': False, 'avg': False, 'sum': False,
        'query': True, '<query>': queries,
        '--limit': '10', '--group-by': 'request_path',
        '--having': '1', '--order-by': 'count',
    }


class TestDynamicSchema(unittest.TestCase):
    """SQLProcessor with fields=None infers the table schema from the data."""

    def test_infers_columns_from_first_record(self):
        proc = ngxtop.SQLProcessor([('t', 'select count(1) as c from log')], None)
        proc.process(iter([{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]))
        self.assertEqual(proc.count(), 2)

    def test_heterogeneous_records_do_not_crash(self):
        # later record is missing key 'b' and has an extra key 'c'; must not raise
        proc = ngxtop.SQLProcessor([('t', 'select count(1) as c from log')], None)
        proc.process(iter([{'a': 1, 'b': 'x'}, {'a': 2, 'c': 'z'}]))
        self.assertEqual(proc.count(), 2)

    def test_empty_input_reports_gracefully(self):
        proc = ngxtop.SQLProcessor([('t', 'select count(1) from log')], None)
        proc.process(iter([]))
        self.assertEqual(proc.count(), 0)
        # report() must not raise even though the table was never created
        self.assertIn('running for', proc.report())


class TestQuerySubcommand(unittest.TestCase):
    """End-to-end test of the `query` subcommand via build_processor."""

    def setUp(self):
        fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.log_file = os.path.join(fixtures_dir, 'json_sample.log')
        if not os.path.isfile(self.log_file):
            self.skipTest("Fixture file not found: %s" % self.log_file)
        with open(self.log_file, 'r') as f:
            self.lines = f.readlines()

    def _records(self):
        return ngxtop.parse_log(self.lines, build_pattern('json'))

    def test_build_processor_query_mode(self):
        args = _query_args(['select status_type, count(1) as cnt from log group by status_type'])
        processor = ngxtop.build_processor(args)
        processor.process(self._records())
        report = processor.report()
        self.assertIn('running for', report)
        self.assertEqual(processor.count(), 5)

    def test_query_aggregation_values(self):
        args = _query_args(['select count(1) as c from log where status_type = 2'])
        processor = ngxtop.build_processor(args)
        processor.process(self._records())
        with __import__('contextlib').closing(processor.conn.cursor()) as cur:
            cur.execute('select count(1) from log where status_type = 2')
            self.assertEqual(cur.fetchone()[0], 2)  # two 200s in the fixture


if __name__ == '__main__':
    unittest.main()
