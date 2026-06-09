#!/usr/bin/env python3
"""Test advanced binary formats: EXE and MSI"""

import sys
import io
import json
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

# Directly load the extractor module
extractor_path = Path(__file__).parent / 'app' / 'services' / 'binary' / 'extractor.py'
spec = spec_from_file_location("extractor", extractor_path)
extractor_module = module_from_spec(spec)
spec.loader.exec_module(extractor_module)

BinaryExtractor = extractor_module.BinaryExtractor


def create_minimal_pe_header():
    """Create a minimal PE/EXE header for testing"""
    # DOS header
    dos_header = b'MZ' + b'\x00' * 58 + b'\x40\x00\x00\x00'  # e_lfanew at offset 0x3C = 0x40
    
    # PE header at offset 0x40
    pe_signature = b'PE\x00\x00'
    
    # COFF header (20 bytes)
    machine = b'\x4c\x01'  # Machine type: x86
    num_sections = b'\x01\x00'  # 1 section
    timestamp = b'\x00\x00\x00\x00'
    ptr_sym = b'\x00\x00\x00\x00'
    num_syms = b'\x00\x00\x00\x00'
    opt_hdr_size = b'\xe0\x00'  # Size of optional header
    characteristics = b'\x02\x01'  # Executable, 32-bit
    
    coff_header = machine + num_sections + timestamp + ptr_sym + num_syms + opt_hdr_size + characteristics
    
    # Optional header (224 bytes minimum)
    magic = b'\x0b\x01'  # PE32
    opt_header = magic + b'\x00' * 222
    
    # Simple text section (40 bytes header)
    section_name = b'.text\x00\x00\x00'
    section_hdr = section_name + b'\x00' * 32
    
    exe_data = dos_header + b'\x00' * (0x40 - len(dos_header)) + pe_signature + coff_header + opt_header + section_hdr + b'\x00' * 512
    
    return exe_data


def create_minimal_msi_data():
    """Create a minimal MSI-like structure (MSI is OLE compound document)"""
    # MSI files are OLE Compound Document Format files
    # For testing, we just create a file with MSI header
    msi_header = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'  # OLE compound file signature
    msi_data = msi_header + b'\x00' * 1024
    return msi_data


def test_exe_format():
    """Test EXE file analysis"""
    print("\n" + "="*60)
    print("TEST: EXE Format Analysis")
    print("="*60)
    
    exe_data = create_minimal_pe_header()
    be = BinaryExtractor()
    res = be.extract('test.exe', exe_data, job_id='exe_test')
    
    print(f"✓ EXE Analysis completed")
    print(f"  Extracted entries: {len(res.extracted_files)}")
    print(f"  Job ID: {res.job_id}")
    print(f"  Metadata: {json.dumps(res.metadata, indent=2)}")
    
    if res.extracted_files:
        print(f"\n  File details:")
        for f in res.extracted_files:
            print(f"    - Path: {f.get('path', 'N/A')}")
            print(f"    - Size: {f['size']} bytes")
            print(f"    - MIME: {f.get('mime_type', 'N/A')}")
    
    return True


def test_msi_format():
    """Test MSI file analysis"""
    print("\n" + "="*60)
    print("TEST: MSI Format Analysis")
    print("="*60)
    
    msi_data = create_minimal_msi_data()
    be = BinaryExtractor()
    res = be.extract('installer.msi', msi_data, job_id='msi_test')
    
    print(f"✓ MSI Analysis completed")
    print(f"  Extracted entries: {len(res.extracted_files)}")
    print(f"  Job ID: {res.job_id}")
    print(f"  Metadata: {json.dumps(res.metadata, indent=2)}")
    
    if res.extracted_files:
        print(f"\n  File details:")
        for f in res.extracted_files:
            print(f"    - Path: {f.get('path', 'N/A')}")
            print(f"    - Size: {f['size']} bytes")
            print(f"    - MIME: {f.get('mime_type', 'N/A')}")
    
    return True


def test_unknown_format():
    """Test handling of unknown binary formats"""
    print("\n" + "="*60)
    print("TEST: Unknown Binary Format Handling")
    print("="*60)
    
    # Random binary data
    unknown_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # PNG-like header but not a real PNG
    
    be = BinaryExtractor()
    res = be.extract('unknown.bin', unknown_data, job_id='unknown_test')
    
    print(f"✓ Unknown format handled gracefully")
    print(f"  Extracted entries: {len(res.extracted_files)}")
    print(f"  Treated as single file: {res.extracted_files[0].get('path')}")
    print(f"  MIME type: {res.extracted_files[0].get('mime_type')}")
    
    return True


def main():
    print("\n" + "="*60)
    print("BINARY FORMAT SUPPORT TEST - Advanced Formats")
    print("="*60)
    
    tests = [
        ("EXE Format", test_exe_format),
        ("MSI Format", test_msi_format),
        ("Unknown Format", test_unknown_format),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            results.append((name, f"ERROR: {str(e)[:50]}"))
            import traceback
            traceback.print_exc()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name:30} {result}")
    
    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    return all(r == "PASS" for _, r in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
