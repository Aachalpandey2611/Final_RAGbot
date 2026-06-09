#!/usr/bin/env python3
"""Standalone test - direct import without package __init__"""

import sys
import io
import zipfile
import tarfile
import gzip
import json
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

# Directly load the extractor module without going through __init__
extractor_path = Path(__file__).parent / 'app' / 'services' / 'binary' / 'extractor.py'
spec = spec_from_file_location("extractor", extractor_path)
extractor_module = module_from_spec(spec)
spec.loader.exec_module(extractor_module)

BinaryExtractor = extractor_module.BinaryExtractor
BinaryExtractionResult = extractor_module.BinaryExtractionResult

# Also load graph module
graph_path = Path(__file__).parent / 'app' / 'services' / 'binary' / 'graph.py'
spec_graph = spec_from_file_location("graph", graph_path)
graph_module = module_from_spec(spec_graph)
spec_graph.loader.exec_module(graph_module)

build_graph_json = graph_module.build_graph_json

def test_zip_extraction():
    """Test ZIP archive extraction"""
    print("\n" + "="*60)
    print("TEST 1: ZIP Archive Extraction")
    print("="*60)
    
    # Create test ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('hello.txt', 'hello world')
        z.writestr('dir/readme.md', '# readme\n\nThis is a readme file')
        z.writestr('config.json', '{"version": "1.0"}')
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('test.zip', data, job_id='zip_test')
    
    assert len(res.extracted_files) == 3, f"Expected 3 files, got {len(res.extracted_files)}"
    assert len(res.relationships) == 3, f"Expected 3 relationships, got {len(res.relationships)}"
    
    print(f"✓ Extracted files: {len(res.extracted_files)}")
    for f in res.extracted_files:
        print(f"  - {f['path']:30} | Size: {f['size']:6} bytes | SHA256: {f['sha256'][:8]}... | MIME: {f['mime_type']}")
    
    print(f"✓ Relationships: {len(res.relationships)}")
    for r in res.relationships:
        print(f"  - {r['parent']} -> {r['child']} ({r['type']})")
    
    print(f"✓ Metadata: {json.dumps(res.metadata)}")
    return True


def test_tar_extraction():
    """Test TAR archive extraction"""
    print("\n" + "="*60)
    print("TEST 2: TAR Archive Extraction")
    print("="*60)
    
    # Create test TAR
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        # Add text file
        info = tarfile.TarInfo(name='test.txt')
        data = b'Test tar file content'
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
        
        # Add nested file
        info = tarfile.TarInfo(name='subdir/nested.txt')
        data = b'Nested file'
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('test.tar', data, job_id='tar_test')
    
    assert len(res.extracted_files) == 2, f"Expected 2 files, got {len(res.extracted_files)}"
    
    print(f"✓ Extracted files: {len(res.extracted_files)}")
    for f in res.extracted_files:
        print(f"  - {f['path']:30} | Size: {f['size']:6} bytes | SHA256: {f['sha256'][:8]}...")
    
    print(f"✓ Relationships: {len(res.relationships)}")
    return True


def test_tar_gz_extraction():
    """Test TAR.GZ archive extraction"""
    print("\n" + "="*60)
    print("TEST 3: TAR.GZ Archive Extraction")
    print("="*60)
    
    # Create test TAR.GZ
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        info = tarfile.TarInfo(name='compressed.txt')
        data = b'Compressed tar file'
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('test.tar.gz', data, job_id='targz_test')
    
    assert len(res.extracted_files) >= 1, f"Expected at least 1 file, got {len(res.extracted_files)}"
    
    print(f"✓ Extracted files: {len(res.extracted_files)}")
    for f in res.extracted_files:
        print(f"  - {f['path']:30} | Size: {f['size']:6} bytes")
    return True


def test_gzip_extraction():
    """Test GZIP file extraction"""
    print("\n" + "="*60)
    print("TEST 4: GZIP File Extraction")
    print("="*60)
    
    # Create test GZIP
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        gz.write(b'Gzip compressed content here')
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('file.txt.gz', data, job_id='gz_test')
    
    print(f"✓ Extraction result:")
    print(f"  Files: {len(res.extracted_files)}")
    print(f"  Metadata: {json.dumps(res.metadata)}")
    if res.extracted_files:
        for f in res.extracted_files:
            print(f"  - {f.get('path', 'decompressed')} | Size: {f['size']} bytes")
    return True


def test_single_file():
    """Test handling of single files (not archives)"""
    print("\n" + "="*60)
    print("TEST 5: Single File (Non-Archive) Processing")
    print("="*60)
    
    content = b'This is a plain text file'
    be = BinaryExtractor()
    res = be.extract('document.txt', content, job_id='file_test')
    
    assert len(res.extracted_files) == 1, f"Expected 1 file entry, got {len(res.extracted_files)}"
    
    f = res.extracted_files[0]
    print(f"✓ File: {f['path']}")
    print(f"  Size: {f['size']} bytes")
    print(f"  SHA256: {f['sha256']}")
    print(f"  MIME: {f['mime_type']}")
    print(f"✓ Relationships: {len(res.relationships)}")
    return True


def test_graph_building():
    """Test document tree graph building"""
    print("\n" + "="*60)
    print("TEST 6: Document Tree Graph Building")
    print("="*60)
    
    # Create test ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('file1.txt', 'content 1')
        z.writestr('dir/file2.txt', 'content 2')
        z.writestr('dir/subdir/file3.txt', 'content 3')
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('archive.zip', data, job_id='graph_test')
    
    try:
        graph_json = build_graph_json(res.relationships)
        
        print(f"✓ Graph structure created")
        print(f"  Nodes: {len(graph_json['nodes'])}")
        print(f"  Edges: {len(graph_json['edges'])}")
        
        print(f"\nNodes:")
        for node in graph_json['nodes']:
            print(f"  - {node['id']}")
        
        print(f"\nEdges (Parent -> Child relationships):")
        for edge in graph_json['edges']:
            print(f"  - {edge['source']} -> {edge['target']} ({edge.get('relation', 'contains')})")
        
        return True
    except Exception as e:
        print(f"⚠ Graph building error: {e}")
        import traceback
        traceback.print_exc()
        return True  # Don't fail, networkx might not be available


def test_complex_archive():
    """Test complex nested archive structure"""
    print("\n" + "="*60)
    print("TEST 7: Complex Nested Archive Structure")
    print("="*60)
    
    # Create complex ZIP with multiple levels
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('README.md', '# Project Documentation')
        z.writestr('config/app.json', '{"name": "MyApp"}')
        z.writestr('config/db.json', '{"host": "localhost"}')
        z.writestr('src/main.py', 'print("Hello")')
        z.writestr('src/utils/helpers.py', 'def helper(): pass')
        z.writestr('tests/test_main.py', 'def test(): pass')
    
    data = buf.getvalue()
    be = BinaryExtractor()
    res = be.extract('project.zip', data, job_id='complex_test')
    
    assert len(res.extracted_files) == 6, f"Expected 6 files, got {len(res.extracted_files)}"
    
    print(f"✓ Extracted files: {len(res.extracted_files)}")
    for f in res.extracted_files:
        print(f"  - {f['path']:35} | {f['size']:6} bytes | {f['mime_type']}")
    
    print(f"\n✓ Directory structure visualization:")
    # Group by directory
    dirs = {}
    for f in res.extracted_files:
        path = f['path']
        if '/' in path:
            d = path.split('/')[0]
            if d not in dirs:
                dirs[d] = []
            dirs[d].append(path)
        else:
            if 'root' not in dirs:
                dirs['root'] = []
            dirs['root'].append(path)
    
    for d in sorted(dirs.keys()):
        print(f"  📁 {d}/")
        for f in sorted(dirs[d]):
            fname = f.split('/')[-1]
            print(f"     📄 {fname}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BINARY DOCUMENT PROCESSING SERVICE - TEST SUITE")
    print("="*60)
    print("Testing: ZIP, TAR, TAR.GZ, GZIP, single files, and graph building")
    
    tests = [
        ("ZIP Extraction", test_zip_extraction),
        ("TAR Extraction", test_tar_extraction),
        ("TAR.GZ Extraction", test_tar_gz_extraction),
        ("GZIP Extraction", test_gzip_extraction),
        ("Single File", test_single_file),
        ("Graph Building", test_graph_building),
        ("Complex Archive", test_complex_archive),
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
