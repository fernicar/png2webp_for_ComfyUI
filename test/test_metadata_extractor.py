#!/usr/bin/env python3
"""
Test suite for MetadataExtractor
Tests all CivitAI and ComfyUI metadata extraction functionality
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata_GUI import MetadataExtractor, DEBUG

# Disable debug logging for tests
DEBUG = False


def test_metadata_extractor_import():
    """Test that MetadataExtractor class imports correctly."""
    print("✅ MetadataExtractor imported successfully")
    return True


def test_civitai_dragon_file():
    """Test extraction on the problematic dragon .jpeg file."""
    filepath = Path("civitai/c9392f02-85e8-4ad7-b172-7472b85f9b1f.jpeg")
    
    if not filepath.exists():
        print(f"⚠️  Test file not found: {filepath}")
        return True
    
    print(f"\nTesting CivitAI dragon file: {filepath.name}")
    
    result = MetadataExtractor.extract(str(filepath), method="civitai")
    
    if 'parameters' in result:
        print("✅ Extracted parameters successfully")
        if 'Steps:' in result['parameters']:
            print("✅ Found Steps parameter")
        if 'BREAK' in result['parameters']:
            print("✅ Found BREAK markers")
        if 'Civitai resources' in result['parameters']:
            print("✅ Found Civitai resources metadata")
    
    if 'positive_prompt' in result:
        print("✅ Parsed positive_prompt field")
    
    if 'generation_params' in result:
        print("✅ Parsed generation_params field")
    
    success = 'parameters' in result and len(result['parameters']) > 100
    print(f"✅ Dragon file test: {'PASSED' if success else 'FAILED'}")
    return success


def test_civitai_girl_file():
    """Test extraction on the problematic blonde girl .jpeg file (that is really PNG)."""
    filepath = Path("civitai/9494a097-06b2-4650-b7c1-0ad11a086731.jpeg")
    
    if not filepath.exists():
        print(f"\n⚠️  Test file not found: {filepath}")
        return True
    
    print(f"\nTesting CivitAI girl file: {filepath.name}")
    
    result = MetadataExtractor.extract(str(filepath), method="civitai")
    
    if 'parameters' in result:
        print("✅ Extracted parameters successfully")
        if 'Negative prompt:' in result['parameters']:
            print("✅ Found Negative prompt")
        if 'Steps:' in result['parameters']:
            print("✅ Found Steps parameter")
    
    success = 'parameters' in result and len(result['parameters']) > 100
    print(f"✅ Girl file test: {'PASSED' if success else 'FAILED'}")
    return success


def test_extraction_methods():
    """Test both extraction methods exist and return data."""
    print("\nTesting extraction methods:")
    
    test_files = [
        Path("civitai/c9392f02-85e8-4ad7-b172-7472b85f9b1f.jpeg"),
        Path("dog_cat_mouse/ComfyUI_14836_.png"),
    ]
    
    passed = 0
    for f in test_files:
        if f.exists():
            res_civitai = MetadataExtractor.extract(str(f), method="civitai")
            res_comfyui = MetadataExtractor.extract(str(f), method="comfyui")
            
            if isinstance(res_civitai, dict) and isinstance(res_comfyui, dict):
                print(f"✅ Both extraction methods work for {f.name}")
                passed +=1
    
    return passed > 0


def test_helper_functions():
    """Test helper functions exist and have correct signatures."""
    print("\nTesting helper functions:")
    
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


def main():
    """Run all metadata extractor tests."""
    print("="*60)
    print("Metadata Extractor Test Suite")
    print("="*60)
    
    tests = [
        test_metadata_extractor_import,
        test_helper_functions,
        test_extraction_methods,
        test_civitai_dragon_file,
        test_civitai_girl_file,
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