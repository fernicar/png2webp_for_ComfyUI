
#!/usr/bin/env python3
"""
Standalone test suite for PNG to WebP converter functions
No external dependencies required
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest import mock

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import png2webp


def test_conversion_function_exists():
    """Test that conversion functions exist."""
    print("Testing conversion functions exist...")
    
    assert hasattr(png2webp, 'saveWebp'), "saveWebp function not found"
    assert hasattr(png2webp, 'convert_png_to_webp'), "convert_png_to_webp function not found"
    
    print("✅ All conversion functions found")
    return True


def test_actual_conversion():
    """Test actual conversion with real test image."""
    print("\nTesting actual PNG to WebP conversion...")
    
    from PIL import Image
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create real test PNG
        img = Image.new('RGB', (100, 100), color='blue')
        test_png = Path(temp_dir) / "test.png"
        img.save(test_png)
        
        # Run real conversion
        result = png2webp.saveWebp(str(test_png), quality=90, method=6)
        
        assert 'filename' in result, "Conversion returned no filename"
        assert result['filename'].endswith('.webp'), "Output is not WebP format"
        assert Path(result['filename']).exists(), "WebP file was not created"
        
        os.remove(result['filename'])
    
    print("✅ Actual conversion works correctly")
    return True


def test_convert_png_to_webp_parameters():
    """Test parameter passing to convert_png_to_webp."""
    print("\nTesting convert_png_to_webp parameters...")
    
    with mock.patch('png2webp.saveWebp') as mock_save:
        mock_save.return_value = {'filename': 'test.webp'}
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('shutil.copystat'):
                png2webp.convert_png_to_webp(
                    "test.png",
                    quality=80,
                    lossless=True,
                    method=4,
                    delete_after=True
                )
        
        mock_save.assert_called_once()
        args = mock_save.call_args
        
        assert args[1]['quality'] == 80, "Quality parameter not passed correctly"
        assert args[1]['lossless'] == True, "Lossless parameter not passed correctly"
        assert args[1]['method'] == 4, "Method parameter not passed correctly"
    
    print("✅ All parameters passed correctly")
    return True


def test_error_handling():
    """Test error handling cases."""
    print("\nTesting error handling...")
    
    # Test non-existent file
    try:
        png2webp.convert_png_to_webp("nonexistent_1234.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("✅ Correctly raised FileNotFoundError for missing file")
    
    # Test wrong file type
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'not a png')
    
    try:
        png2webp.convert_png_to_webp(f.name)
        assert False, "Should have raised ValueError for non-PNG file"
    except ValueError:
        print("✅ Correctly raised ValueError for non-PNG file")
    finally:
        os.unlink(f.name)
    
    return True


def main():
    """Run all converter tests."""
    print("="*60)
    print("PNG to WebP Converter Test Suite")
    print("="*60)
    
    tests = [
        test_conversion_function_exists,
        test_convert_png_to_webp_parameters,
        test_error_handling,
        test_actual_conversion,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed +=1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
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
