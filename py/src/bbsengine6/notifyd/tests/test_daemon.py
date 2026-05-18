# notifyd/tests/test_daemon.py
# Tests for daemon and CLI

import pytest
from unittest.mock import MagicMock, patch, call
import threading
import signal

from bbsengine6.notifyd import daemon as daemon_module


class TestNotifyDaemon:
    """Test NotifyDaemon class"""

    def test_init(self):
        """Initialize daemon"""
        config = {"imap_servers": []}
        d = daemon_module.NotifyDaemon(config)
        
        assert d.config == config
        assert d.running is False
        assert d._threads == []

    def test_start_sets_running(self):
        """Start sets running flag"""
        config = {}
        d = daemon_module.NotifyDaemon(config)
        
        # Mock to prevent actual thread from running
        with patch.object(d, '_monitor_loop'):
            with patch('signal.signal'):
                try:
                    # Start in a thread so we can stop it
                    start_thread = threading.Thread(target=d.start)
                    start_thread.daemon = True
                    start_thread.start()
                    
                    # Give it time to start
                    import time
                    time.sleep(0.1)
                    
                    assert d.running is True
                finally:
                    d.stop()

    def test_stop_clears_running(self):
        """Stop clears running flag"""
        config = {}
        d = daemon_module.NotifyDaemon(config)
        d.running = True
        d._stop_event = threading.Event()
        
        d.stop()
        
        assert d.running is False

    def test_already_running(self):
        """Can't start if already running"""
        config = {}
        d = daemon_module.NotifyDaemon(config)
        d.running = True
        
        with patch('signal.signal'):
            # Should return early
            d.start()
        
        assert d.running is True

    def test_handle_signal_stops_daemon(self):
        """Signal handler stops daemon"""
        config = {}
        d = daemon_module.NotifyDaemon(config)
        d.running = True
        d._stop_event = threading.Event()
        
        with patch.object(d, 'stop') as mock_stop:
            d._handle_signal(signal.SIGTERM, None)
            mock_stop.assert_called_once()

    def test_monitor_loop_sleeps_and_checks_stop(self):
        """Monitor loop sleeps and checks stop event"""
        config = {"imap_servers": [{"poll_interval": 1}]}
        d = daemon_module.NotifyDaemon(config)
        d.running = True
        d._stop_event = threading.Event()
        
        # Simulate stop after first iteration
        original_wait = d._stop_event.wait
        call_count = [0]
        
        def mock_wait(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 1:
                return True  # Signal stop
            return original_wait(*args, **kwargs)
        
        d._stop_event.wait = mock_wait
        
        d._monitor_loop()
        
        # Should have called wait at least once
        assert call_count[0] >= 1

    def test_monitor_loop_handles_errors(self):
        """Monitor loop handles errors gracefully"""
        config = {}
        d = daemon_module.NotifyDaemon(config)
        d.running = True
        d._stop_event = threading.Event()
        
        # Make _stop_event.wait raise then return True
        call_count = [0]
        def mock_wait(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Test error")
            return True
        
        d._stop_event.wait = mock_wait
        
        # Should not raise
        d._monitor_loop()


class TestDaemonFunctions:
    """Test module-level daemon functions"""

    def test_start_daemon_success(self):
        """Start daemon successfully"""
        config = {}
        
        with patch.object(daemon_module.NotifyDaemon, 'start'):
            daemon = daemon_module.start_daemon(config)
            
            assert daemon is not None
            assert isinstance(daemon, daemon_module.NotifyDaemon)

    def test_start_daemon_failure(self):
        """Start daemon handles failure"""
        config = {}
        
        with patch.object(daemon_module.NotifyDaemon, 'start', side_effect=Exception("start failed")):
            with pytest.raises(daemon_module.DaemonError):
                daemon_module.start_daemon(config)

    def test_stop_daemon_with_instance(self):
        """Stop specific daemon instance"""
        d = daemon_module.NotifyDaemon({})
        d.stop = MagicMock()
        
        daemon_module.stop_daemon(d)
        
        d.stop.assert_called_once()

    def test_stop_daemon_global(self):
        """Stop global daemon"""
        # Set global daemon
        d = daemon_module.NotifyDaemon({})
        d.stop = MagicMock()
        daemon_module._global_daemon = d
        
        daemon_module.stop_daemon()
        
        d.stop.assert_called_once()
        assert daemon_module._global_daemon is None

    def test_is_running_true(self):
        """Check daemon is running"""
        d = daemon_module.NotifyDaemon({})
        d.running = True
        
        assert daemon_module.is_running(d) is True

    def test_is_running_false(self):
        """Check daemon not running"""
        d = daemon_module.NotifyDaemon({})
        d.running = False
        
        assert daemon_module.is_running(d) is False


class TestDaemonError:
    """Test DaemonError exception"""

    def test_daemon_error_is_exception(self):
        """DaemonError is an Exception"""
        error = daemon_module.DaemonError("Test error")
        assert isinstance(error, Exception)

    def test_daemon_error_message(self):
        """DaemonError preserves message"""
        error = daemon_module.DaemonError("Daemon startup failed")
        assert str(error) == "Daemon startup failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
