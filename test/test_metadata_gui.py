#!/usr/bin/env python3
"""
Test suite for Metadata Viewer GUI
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_gui_imports():
    """Test that all GUI components can be imported successfully."""
    print("Testing GUI imports...")
    
    try:
        from metadata_GUI import MetadataExtractor, MetadataViewerView
        print("✅ MetadataExtractor imported successfully")
        print("✅ MetadataViewerView imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_metadata_extractor_import():
    """Test metadata extractor public API."""
    print("\nTesting metadata extractor public API...")
    
    from metadata_GUI import MetadataExtractor
    
    public_methods = [
        'extract',
        'extract_from_png',
        'extract_from_webp',
        'get_full_metadata',
    ]
    
    all_found = True
    for method in public_methods:
        if hasattr(MetadataExtractor, method):
            print(f"✅ Found public method: {method}")
        else:
            print(f"❌ Missing public method: {method}")
            all_found = False
    
    return all_found


def test_metadata_extractor_helpers():
    """Test metadata extractor helper functions exist."""
    print("\nTesting metadata extractor helper functions...")
    
    from metadata_GUI import MetadataExtractor
    
    helpers = [
        '_extract_raw_unicode_metadata',
        '_parse_civitai_parameters',
        '_extract_xmp_metadata',
        '_extract_exif_usercomment',
        '_extract_civitai_exif_fallback',
        '_extract_comfyui_exif',
    ]
    
    all_found = True
    for helper in helpers:
        if hasattr(MetadataExtractor, helper):
            print(f"✅ Found helper: {helper}")
        else:
            print(f"❌ Missing helper: {helper}")
            all_found = False
    
    return all_found


def test_extraction_methods():
    """Test both extraction methods exist and are callable."""
    print("\nTesting extraction methods...")
    
    from metadata_GUI import MetadataExtractor
    
    # Test both method types
    methods = ['comfyui', 'civitai']
    
    test_file = Path("dog_cat_mouse/ComfyUI_14836_.png")
    if test_file.exists():
        for method in methods:
            result = MetadataExtractor.extract(str(test_file), method=method)
            assert isinstance(result, dict), f"Method {method} returned invalid type"
            print(f"✅ Extraction method '{method}' works correctly")
    
    return True


def test_gui_creation():
    """Test that GUI window can be created without showing."""
    print("\nTesting GUI window creation...")
    
    from metadata_GUI import QApplication, MetadataViewerView
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        # Create window without showing it
        window = MetadataViewerView()
        window.close()
        print("✅ GUI window created successfully")
        return True
    except Exception as e:
        print(f"❌ GUI creation failed: {e}")
        return False


def main():
    """Run all GUI tests."""
    print("="*60)
    print("Metadata Viewer GUI Test Suite")
    print("="*60)
    
    tests = [
        test_gui_imports,
        test_metadata_extractor_import,
        test_metadata_extractor_helpers,
        test_extraction_methods,
        test_gui_creation,
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
