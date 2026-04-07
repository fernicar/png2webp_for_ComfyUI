#!/usr/bin/env python3
"""
Test suite for PNG to WebP Converter GUI (main.py)
"""

import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_gui_imports():
    """Test that all main GUI components can be imported successfully."""
    print("Testing main GUI imports...")
    
    try:
        from main import PNG2WebPView, ConversionProcessor
        print("✅ PNG2WebPView imported successfully")
        print("✅ ConversionProcessor imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_gui_classes_exist():
    """Test main GUI classes and methods exist."""
    print("\nTesting main GUI class structure...")
    
    from main import PNG2WebPView
    
    required_methods = [
        'select_files',
        'select_folder',
        'start_conversion',
        'stop_conversion',
        'update_progress',
        'add_conversion_result',
    ]
    
    all_found = True
    for method in required_methods:
        if hasattr(PNG2WebPView, method):
            print(f"✅ Found GUI method: {method}")
        else:
            print(f"❌ Missing GUI method: {method}")
            all_found = False
    
    return all_found


def test_conversion_processor():
    """Test ConversionProcessor class."""
    print("\nTesting ConversionProcessor class...")
    
    from main import ConversionProcessor
    
    test_files = ["test1.png", "test2.png"]
    settings = {'quality':90, 'method':6, 'lossless':False}
    
    processor = ConversionProcessor(test_files, settings)
    
    assert hasattr(processor, 'process_next_file'), "Missing process_next_file method"
    assert hasattr(processor, 'stop'), "Missing stop method"
    
    print("✅ ConversionProcessor class is correctly structured")
    return True


def test_gui_creation():
    """Test that main GUI window can be created without showing."""
    print("\nTesting main GUI window creation...")
    
    from main import QApplication, PNG2WebPView
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        # Create window without showing it
        window = PNG2WebPView()
        window.close()
        print("✅ Main GUI window created successfully")
        return True
    except Exception as e:
        print(f"❌ GUI creation failed: {e}")
        return False


def test_gui_settings():
    """Test GUI controls and default values."""
    print("\nTesting GUI default settings...")
    
    from main import QApplication, PNG2WebPView
    
    app = QApplication.instance() or QApplication(sys.argv)
    window = PNG2WebPView()
    
    defaults_ok = True
    
    if window.quality_spinbox.value() == 90:
        print("✅ Default quality is correct (90)")
    else:
        print(f"❌ Default quality incorrect: {window.quality_spinbox.value()}")
        defaults_ok = False
    
    if window.method_combo.currentIndex() == 6:
        print("✅ Default compression method is correct (6)")
    else:
        print(f"❌ Default compression method incorrect: {window.method_combo.currentIndex()}")
        defaults_ok = False
    
    window.close()
    return defaults_ok


def main():
    """Run all main GUI tests."""
    print("="*60)
    print("PNG to WebP Converter GUI Test Suite")
    print("="*60)
    
    tests = [
        test_gui_imports,
        test_gui_classes_exist,
        test_conversion_processor,
        test_gui_creation,
        test_gui_settings,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed +=1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
