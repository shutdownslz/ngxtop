import unittest
import os
import tempfile
import shutil
import time
import threading
from unittest.mock import patch, MagicMock

from ngxtop import ngxtop


class TestLogRotation(unittest.TestCase):
    """Test log rotation handling functionality."""
    
    def setUp(self):
        """Set up test environment with temporary files."""
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, 'test.log')
        
        # Create initial log file
        with open(self.log_file, 'w') as f:
            f.write('Initial log entry\n')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_should_reopen_file_inode_change(self):
        """Test inode change detection."""
        # Get initial inode
        initial_stat = os.stat(self.log_file)
        initial_inode = initial_stat.st_ino
        initial_size = initial_stat.st_size
        
        # Move file and create new one (simulating rotation)
        rotated_file = self.log_file + '.1'
        os.rename(self.log_file, rotated_file)
        
        with open(self.log_file, 'w') as f:
            f.write('New log file after rotation\n')
        
        # Should detect rotation due to inode change
        should_reopen = ngxtop._should_reopen_file(self.log_file, initial_inode, initial_size)
        self.assertTrue(should_reopen)
    
    def test_should_reopen_file_size_decrease(self):
        """Test file size decrease detection."""
        # Create a larger file
        with open(self.log_file, 'w') as f:
            f.write('A' * 2000)  # 2000 bytes
        
        initial_stat = os.stat(self.log_file)
        initial_inode = initial_stat.st_ino
        initial_size = initial_stat.st_size
        
        # Truncate the file (simulating rotation by truncation)
        with open(self.log_file, 'w') as f:
            f.write('Small file\n')  # Much smaller
        
        # Should detect rotation due to significant size decrease
        should_reopen = ngxtop._should_reopen_file(self.log_file, initial_inode, initial_size)
        self.assertTrue(should_reopen)
    
    def test_should_not_reopen_file_normal_growth(self):
        """Test that normal file growth doesn't trigger rotation."""
        initial_stat = os.stat(self.log_file)
        initial_inode = initial_stat.st_ino
        initial_size = initial_stat.st_size
        
        # Append to file (normal growth)
        with open(self.log_file, 'a') as f:
            f.write('New log entry\n')
        
        # Should NOT detect rotation
        should_reopen = ngxtop._should_reopen_file(self.log_file, initial_inode, initial_size)
        self.assertFalse(should_reopen)
    
    def test_should_reopen_file_missing(self):
        """Test handling of missing file."""
        initial_stat = os.stat(self.log_file)
        initial_inode = initial_stat.st_ino
        initial_size = initial_stat.st_size
        
        # Remove the file
        os.remove(self.log_file)
        
        # Should detect need to reopen
        should_reopen = ngxtop._should_reopen_file(self.log_file, initial_inode, initial_size)
        self.assertTrue(should_reopen)
    
    def test_open_file_with_retry_success(self):
        """Test successful file opening with retry."""
        file_handle, inode, size = ngxtop._open_file_with_retry(self.log_file, 3)
        
        self.assertIsNotNone(file_handle)
        self.assertIsNotNone(inode)
        self.assertGreater(size, 0)
        
        file_handle.close()
    
    def test_open_file_with_retry_failure(self):
        """Test file opening failure after retries."""
        non_existent_file = os.path.join(self.test_dir, 'does_not_exist.log')
        
        with patch('time.sleep'):  # Speed up test by mocking sleep
            file_handle, inode, size = ngxtop._open_file_with_retry(non_existent_file, 2)
            
            self.assertIsNone(file_handle)
            self.assertIsNone(inode)
            self.assertEqual(size, 0)
    
    def test_rotation_signal_handling(self):
        """Test SIGHUP signal handling."""
        # Check initial state
        self.assertFalse(ngxtop._check_rotation_signal())
        
        # Simulate SIGHUP
        ngxtop._sighup_handler(1, None)  # signum=1 (SIGHUP), frame=None
        
        # Should be flagged for rotation
        self.assertTrue(ngxtop._check_rotation_signal())
        
        # Clear the flag
        ngxtop._clear_rotation_signal()
        
        # Should be cleared
        self.assertFalse(ngxtop._check_rotation_signal())


if __name__ == '__main__':
    unittest.main()