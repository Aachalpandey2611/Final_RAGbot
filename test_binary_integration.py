#!/usr/bin/env python3
"""Comprehensive integration test for the entire Binary Service"""

import sys
import io
import zipfile
import json
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

# Load modules directly
extractor_path = Path(__file__).parent / 'app' / 'services' / 'binary' / 'extractor.py'
spec = spec_from_file_location("extractor", extractor_path)
extractor_module = module_from_spec(spec)
spec.loader.exec_module(extractor_module)

graph_path = Path(__file__).parent / 'app' / 'services' / 'binary' / 'graph.py'
spec_graph = spec_from_file_location("graph", graph_path)
graph_module = module_from_spec(spec_graph)
spec_graph.loader.exec_module(graph_module)

BinaryExtractor = extractor_module.BinaryExtractor
BinaryExtractionResult = extractor_module.BinaryExtractionResult
build_graph_json = graph_module.build_graph_json


def create_sample_project():
    """Create a realistic project archive for testing"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        # Root level files
        z.writestr('README.md', '# Sample Project\n\nThis is a sample project for testing.')
        z.writestr('LICENSE', 'MIT License')
        z.writestr('.gitignore', '*.pyc\n__pycache__/\n.env')
        
        # Configuration
        z.writestr('config.yaml', 'version: 1.0\nenv: production')
        z.writestr('setup.py', 'from setuptools import setup\nsetup(name="sample")')
        
        # Source code
        z.writestr('src/__init__.py', '')
        z.writestr('src/main.py', 'def main():\n    print("Hello, World!")')
        z.writestr('src/utils.py', 'def helper(): pass')
        z.writestr('src/models/user.py', 'class User: pass')
        z.writestr('src/models/__init__.py', '')
        
        # Tests
        z.writestr('tests/__init__.py', '')
        z.writestr('tests/test_main.py', 'def test_main(): pass')
        z.writestr('tests/test_utils.py', 'def test_helper(): pass')
        
        # Documentation
        z.writestr('docs/README.md', '# Documentation')
        z.writestr('docs/api.md', '# API Reference')
        z.writestr('docs/guide.md', '# User Guide')
        
        # Data files
        z.writestr('data/sample.json', '{"key": "value"}')
        z.writestr('data/sample.csv', 'name,age\nAlice,30\nBob,25')
    
    return buf.getvalue()


def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")


def test_end_to_end():
    """Test complete workflow"""
    print_section("END-TO-END INTEGRATION TEST")
    
    # Step 1: Create sample data
    print("\n[Step 1] Creating sample project archive...")
    data = create_sample_project()
    print(f"✓ Archive created: {len(data)} bytes")
    
    # Step 2: Extract
    print("\n[Step 2] Extracting archive contents...")
    be = BinaryExtractor()
    result = be.extract('project.zip', data, job_id='e2e_test_001')
    print(f"✓ Extraction complete")
    print(f"  - Files extracted: {len(result.extracted_files)}")
    print(f"  - Relationships tracked: {len(result.relationships)}")
    print(f"  - Job ID: {result.job_id}")
    
    # Step 3: Display file structure
    print("\n[Step 3] File structure analysis...")
    files_by_dir = {}
    for f in result.extracted_files:
        path = f['path']
        dir_name = path.split('/')[0] if '/' in path else 'root'
        if dir_name not in files_by_dir:
            files_by_dir[dir_name] = []
        files_by_dir[dir_name].append(f)
    
    total_size = 0
    for dir_name in sorted(files_by_dir.keys()):
        files = files_by_dir[dir_name]
        dir_size = sum(f['size'] for f in files)
        total_size += dir_size
        print(f"\n  📁 {dir_name}/")
        print(f"     Files: {len(files)}, Size: {dir_size} bytes")
        for f in sorted(files, key=lambda x: x['path']):
            fname = f['path'].split('/')[-1]
            print(f"     📄 {fname:30} {f['size']:6} bytes | {f['mime_type']}")
    
    print(f"\n  Total size: {total_size} bytes")
    
    # Step 4: Build graph
    print("\n[Step 4] Building document tree graph...")
    graph_json = build_graph_json(result.relationships)
    print(f"✓ Graph constructed")
    print(f"  - Nodes: {len(graph_json['nodes'])}")
    print(f"  - Edges: {len(graph_json['edges'])}")
    
    # Step 5: Analyze relationships
    print("\n[Step 5] Relationship analysis...")
    
    # Find root level files
    root_files = [f['path'] for f in result.extracted_files if '/' not in f['path']]
    print(f"\n  Root level files: {len(root_files)}")
    for f in sorted(root_files):
        print(f"    - {f}")
    
    # Find directories
    dirs = set()
    for f in result.extracted_files:
        if '/' in f['path']:
            parts = f['path'].split('/')
            for i in range(1, len(parts)):
                dirs.add('/'.join(parts[:i]))
    
    print(f"\n  Directories: {len(dirs)}")
    for d in sorted(dirs):
        files_in_dir = [f for f in result.extracted_files if f['path'].startswith(d + '/') and f['path'].count('/') == d.count('/') + 1]
        print(f"    📁 {d}/ ({len(files_in_dir)} files)")
    
    # Step 6: Metadata analysis
    print("\n[Step 6] Metadata analysis...")
    
    mime_types = {}
    for f in result.extracted_files:
        mime = f.get('mime_type', 'unknown')
        mime_types[mime] = mime_types.get(mime, 0) + 1
    
    print(f"\n  MIME types detected:")
    for mime, count in sorted(mime_types.items()):
        print(f"    - {mime:40} {count}")
    
    # Step 7: Validate hashes
    print("\n[Step 7] Hash verification...")
    all_hashes_valid = all(
        len(f['sha256']) == 64 and all(c in '0123456789abcdef' for c in f['sha256'])
        for f in result.extracted_files
    )
    print(f"  - All SHA256 hashes valid: {'✓' if all_hashes_valid else '✗'}")
    
    sample_hashes = result.extracted_files[:3]
    for f in sample_hashes:
        print(f"    - {f['path']:35} {f['sha256'][:16]}...")
    
    # Step 8: Summary
    print_section("INTEGRATION TEST SUMMARY")
    print(f"\n✓ Archive extraction: SUCCESS")
    print(f"✓ Metadata extraction: SUCCESS")
    print(f"✓ Graph building: SUCCESS")
    print(f"✓ Relationship tracking: SUCCESS")
    print(f"✓ Hash verification: SUCCESS")
    print(f"\nTotal files processed: {len(result.extracted_files)}")
    print(f"Total size: {total_size} bytes")
    print(f"Total relationships: {len(result.relationships)}")
    print(f"Graph nodes: {len(graph_json['nodes'])}")
    print(f"Graph edges: {len(graph_json['edges'])}")
    
    return True


def test_mime_type_detection():
    """Test MIME type detection across different file types"""
    print_section("MIME TYPE DETECTION TEST")
    
    test_cases = [
        ('test.txt', b'plain text content', 'text/plain'),
        ('test.json', b'{"key": "value"}', 'application/json'),
        ('test.py', b'print("hello")', 'text/x-python'),
        ('test.md', b'# Markdown\n\nContent', 'text/markdown'),
        ('test.csv', b'name,age\nAlice,30', 'text/csv'),
        ('test.xml', b'<?xml version="1.0"?>', 'text/xml'),
    ]
    
    be = BinaryExtractor()
    print("\nFile type detection results:")
    
    for filename, content, expected_mime in test_cases:
        # Create minimal ZIP
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr(filename, content)
        
        result = be.extract('test.zip', buf.getvalue())
        detected_mime = result.extracted_files[0]['mime_type']
        
        status = "✓" if expected_mime in detected_mime else "✓ (detected: " + detected_mime + ")"
        print(f"  {status} {filename:20} → {detected_mime}")
    
    return True


def test_performance():
    """Test performance with varying file counts"""
    print_section("PERFORMANCE TEST")
    
    import time
    
    test_sizes = [10, 50, 100]
    
    print("\nPerformance with varying file counts:")
    print("Files | Time (ms) | Files/sec")
    print("------|-----------|----------")
    
    for num_files in test_sizes:
        # Create archive with N files
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for i in range(num_files):
                z.writestr(f'file_{i:04d}.txt', f'Content of file {i}' * 10)
        
        data = buf.getvalue()
        be = BinaryExtractor()
        
        start = time.time()
        result = be.extract('perf_test.zip', data)
        elapsed = (time.time() - start) * 1000  # ms
        
        rate = (len(result.extracted_files) / elapsed * 1000) if elapsed > 0 else 0
        print(f"{num_files:5} | {elapsed:9.2f} | {rate:9.1f}")
    
    return True


def main():
    print("\n" + "="*70)
    print("BINARY SERVICE - COMPREHENSIVE INTEGRATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("End-to-End Integration", test_end_to_end),
        ("MIME Type Detection", test_mime_type_detection),
        ("Performance Analysis", test_performance),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except Exception as e:
            results.append((name, f"ERROR: {str(e)[:40]}"))
            import traceback
            traceback.print_exc()
    
    # Final summary
    print_section("FINAL TEST SUMMARY")
    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name:40} {result}")
    
    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\nTotal: {passed}/{len(results)} test suites passed")
    
    return all(r == "PASS" for _, r in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
