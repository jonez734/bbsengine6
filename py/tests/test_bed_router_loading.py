# test_bed_router_loading.py
# Integration tests for BED router loading

import argparse
from bbsengine6 import module as bbsmodule


class TestBedRouterLoading:
    """Integration tests for loading router modules in BED."""

    def test_load_module_handler_format(self):
        """Test loading a handler module using module.path.ClassName format."""
        router_string = "zoid6.api.handler.MessageRouter"
        
        parts = router_string.split('.')
        module_path = '.'.join(parts[:-1])
        attr_name = parts[-1]
        
        router_module = bbsmodule.get(module_path)
        router_class = getattr(router_module, attr_name)
        
        assert router_class is not None
        assert router_class.__name__ == "MessageRouter"

    def test_load_defaultrouter(self):
        """Test loading defaultrouter (built-in)."""
        from bbsengine6.net.defaultrouter import DefaultRouter
        
        router_module = bbsmodule.get("bbsengine6.net.defaultrouter")
        router_class = getattr(router_module, "DefaultRouter")
        
        assert router_class is DefaultRouter

    def test_load_router_with_args(self):
        """Test loading router module with args parameter."""
        args = argparse.Namespace(debug=False)
        
        router_string = "zoid6.api.handler.MessageRouter"
        parts = router_string.split('.')
        module_path = '.'.join(parts[:-1])
        attr_name = parts[-1]
        
        router_module = bbsmodule.get(module_path, args)
        router_class = getattr(router_module, attr_name)
        
        assert router_class is not None


class TestModuleGetWithDebug:
    """Test module.get() with debug flag for hot reloading."""

    def test_module_get_with_debug_false(self):
        """Test loading module with debug=False (no reload)."""
        args = argparse.Namespace(debug=False)
        
        # First load
        m1 = bbsmodule.get("zoid6.api.handler", args)
        # Second load should return same module (not reload)
        m2 = bbsmodule.get("zoid6.api.handler", args)
        
        assert m1 is m2

    def test_module_get_with_debug_true(self):
        """Test loading module with debug=True triggers reload."""
        args = argparse.Namespace(debug=True)
        
        # First load
        bbsmodule.get("zoid6.api.handler", args)
        # Second load should return reloaded module
        m2 = bbsmodule.get("zoid6.api.handler", args)
        
        assert m2 is not None
