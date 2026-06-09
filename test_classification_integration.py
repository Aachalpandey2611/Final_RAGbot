#!/usr/bin/env python3
"""
Advanced Integration Test for Document Classification
Tests end-to-end workflow including batch processing and metadata extraction
"""

import sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

# Load classifier module
classifier_path = Path(__file__).parent / 'app' / 'services' / 'classification.py'
spec = spec_from_file_location("classification", classifier_path)
classification_module = module_from_spec(spec)
spec.loader.exec_module(classification_module)

DocumentClassifier = classification_module.DocumentClassifier
DocumentClass = classification_module.DocumentClass


def create_test_documents():
    """Create a diverse set of test documents"""
    return [
        ("""PRIVACY POLICY
        Last Updated: June 1, 2024
        
        This Privacy Policy governs the use of our website. We are committed to protecting your privacy.
        The information we collect is used in accordance with this policy and applicable laws.
        All users shall comply with the terms and conditions outlined herein.
        """, "privacy_policy.txt", DocumentClass.POLICIES),
        
        ("""import asyncio
        from typing import List, Optional
        
        async def fetch_user_data(user_id: int) -> Optional[dict]:
            '''Fetch user data from API'''
            async with aiohttp.ClientSession() as session:
                async with session.get(f'/api/users/{user_id}') as resp:
                    return await resp.json()
        
        class Database:
            def __init__(self, connection_string: str):
                self.conn = connection_string
        """, "user_service.py", DocumentClass.SOURCE_CODE),
        
        ("""SYSTEM ARCHITECTURE DESIGN
        Version 2.1
        
        1. Overview
        This document outlines the technical specifications for our cloud infrastructure.
        
        2. Components
        - API Gateway: Nginx with load balancing
        - Message Queue: RabbitMQ cluster
        - Database: PostgreSQL 14.x
        
        3. Deployment
        Services are containerized using Docker and orchestrated with Kubernetes.
        All specifications conform to industry standards.
        """, "architecture.md", DocumentClass.TECHNICAL_DOCUMENTS),
        
        ("""PRODUCT USER MANUAL
        Version 3.2
        
        Chapter 1: Installation
        To install this software:
        Step 1: Download the installer
        Step 2: Run the setup wizard
        Step 3: Follow the on-screen prompts
        Step 4: Restart your computer
        
        Chapter 2: Basic Operations
        How to use the application:
        1. Launch the application from the Start menu
        2. Enter your credentials
        3. Select "New Document"
        """, "user_manual.pdf", DocumentClass.MANUALS),
        
        ("""SERVICE DEPLOYMENT PROCEDURE
        Date: June 2024
        
        Procedure Steps:
        Step 1: Preparation
        - Verify all tests pass
        - Create backup of current version
        - Notify stakeholders
        
        Step 2: Deployment
        - Build Docker images
        - Push to registry
        - Update Kubernetes deployment
        
        Step 3: Verification
        - Run smoke tests
        - Verify all services healthy
        - Monitor for errors
        """, "deployment_procedure.txt", DocumentClass.PROCEDURES),
        
        ("""MEETING MINUTES - Q2 PLANNING
        Date: June 1, 2024
        Time: 10:00 AM
        Attendees: John (PM), Sarah (Tech Lead), Mike (Design), Lisa (QA)
        
        Topics Discussed:
        - Q2 roadmap: 90% finalized
        - Resource allocation: Additional engineers approved
        - Timeline: Launch scheduled for June 30
        
        Action Items:
        1. Sarah: Finalize API specs (Due: June 5)
        2. Mike: Complete wireframes (Due: June 7)
        3. Lisa: Prepare test plan (Due: June 8)
        
        Next Meeting: June 8, 2024
        """, "q2_planning_minutes.txt", DocumentClass.MEETING_NOTES),
        
        ("""SERVICE AGREEMENT
        
        This Agreement made this 1st day of June, 2024
        
        BETWEEN: ABC Corporation ("Client")
        AND: XYZ Services LLC ("Provider")
        
        WHEREAS, the Provider agrees to provide software development services;
        
        NOW THEREFORE in consideration of the mutual covenants:
        
        1. SERVICES: Provider shall develop according to specifications provided.
        
        2. PAYMENT: Client shall pay $100,000 in installments:
           - 30% upon signing
           - 35% at milestone completion
           - 35% at final delivery
        
        3. LIABILITY: Neither party liable for consequential damages.
        
        4. TERM: This agreement is effective for 12 months.
        """, "development_agreement.docx", DocumentClass.CONTRACTS),
        
        ("""Subject: Quarterly Review Complete
        
        Hi Sarah,
        
        I hope this email finds you well. I wanted to reach out regarding the quarterly review process.
        
        As discussed in our last meeting, all reviews have been completed and compiled. The summary shows:
        - 95% of team met objectives
        - Strong performance in Q2
        - Budget allocation approved for Q3
        
        Please let me know if you need any additional information. I'm available for a follow-up call.
        
        Best regards,
        Human Resources Team
        """, "quarterly_review_email.eml", DocumentClass.EMAILS),
    ]


def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")


def test_document_classification_pipeline():
    """Test the full document classification pipeline"""
    print_section("DOCUMENT CLASSIFICATION PIPELINE TEST")
    
    classifier = DocumentClassifier(use_embeddings=False)
    documents = create_test_documents()
    
    print(f"\n✓ Testing {len(documents)} diverse documents...\n")
    
    results = []
    for text, filename, expected_class in documents:
        result = classifier.classify(text, filename)
        results.append({
            "filename": filename,
            "expected": expected_class.value,
            "predicted": result.primary_class.value,
            "confidence": result.confidence,
            "correct": result.primary_class == expected_class,
            "tags": result.tags,
        })
    
    # Display results
    correct = 0
    for result in results:
        status = "✓" if result["correct"] else "✗"
        print(f"{status} {result['filename']:35} | Predicted: {result['predicted']:20} | Confidence: {result['confidence']:.0%}")
        if not result["correct"]:
            print(f"  Expected: {result['expected']}")
        correct += result["correct"]
    
    accuracy = 100*correct/len(results)
    print(f"\n✓ Accuracy: {correct}/{len(results)} ({accuracy:.0f}%)")
    
    # Accept 75%+ accuracy as success (real-world texts can be ambiguous)
    return accuracy >= 75.0


def test_metadata_extraction():
    """Test metadata extraction for each document"""
    print_section("METADATA EXTRACTION TEST")
    
    classifier = DocumentClassifier(use_embeddings=False)
    documents = create_test_documents()
    
    print(f"\n✓ Extracting metadata from {len(documents)} documents...\n")
    
    for text, filename, _ in documents[:3]:  # Test first 3
        result = classifier.classify(text, filename)
        print(f"\nDocument: {filename}")
        print(f"  Classification: {result.primary_class.value}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Metadata:")
        stats = result.metadata.get("text_statistics", {})
        print(f"    - Characters: {stats.get('total_characters', 0)}")
        print(f"    - Words: {stats.get('total_words', 0)}")
        print(f"    - Lines: {stats.get('total_lines', 0)}")
        print(f"    - Avg line length: {stats.get('avg_line_length', 0):.1f}")
    
    return True


def test_confidence_distribution():
    """Analyze confidence score distribution"""
    print_section("CONFIDENCE SCORE ANALYSIS")
    
    classifier = DocumentClassifier(use_embeddings=False)
    documents = create_test_documents()
    
    results = classifier.classify_batch([(text, f"doc_{i}") for i, (text, _, _) in enumerate(documents)])
    
    # Analyze confidence levels
    high_conf = sum(1 for r in results if r.confidence > 0.8)
    medium_conf = sum(1 for r in results if 0.5 < r.confidence <= 0.8)
    low_conf = sum(1 for r in results if r.confidence <= 0.5)
    
    print(f"\n✓ Confidence Distribution across {len(results)} documents:")
    print(f"  High confidence (>80%):   {high_conf} documents")
    print(f"  Medium confidence (50-80%): {medium_conf} documents")
    print(f"  Low confidence (<50%):    {low_conf} documents")
    print(f"  Average confidence: {sum(r.confidence for r in results) / len(results):.1%}")
    
    # Show details
    print(f"\n  Detailed breakdown:")
    for i, result in enumerate(results):
        print(f"    {i+1}. {result.primary_class.value:25} - {result.confidence:.0%}")
    
    return True


def test_class_information_retrieval():
    """Test retrieval of classification class information"""
    print_section("CLASS INFORMATION RETRIEVAL TEST")
    
    classifier = DocumentClassifier(use_embeddings=False)
    
    print(f"\n✓ Supported Document Classes:\n")
    
    for doc_class in DocumentClass:
        info = classifier.get_class_info(doc_class)
        print(f"\n  {info['class']}")
        print(f"    Keywords: {', '.join(info['keywords'][:5])}...")
        print(f"    Characteristics: {', '.join(info['characteristics'])}")
    
    return True


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print_section("EDGE CASES TEST")
    
    classifier = DocumentClassifier(use_embeddings=False)
    
    # Test 1: Very short text
    print(f"\n✓ Test 1: Very short text")
    short_text = "def hello(): pass"
    result = classifier.classify(short_text)
    print(f"  Input: '{short_text}'")
    print(f"  Classification: {result.primary_class.value} ({result.confidence:.0%})")
    assert result.primary_class == DocumentClass.SOURCE_CODE
    
    # Test 2: Ambiguous text
    print(f"\n✓ Test 2: Ambiguous text")
    ambiguous = "This is a document. It contains text."
    result = classifier.classify(ambiguous)
    print(f"  Input: '{ambiguous}'")
    print(f"  Classification: {result.primary_class.value} ({result.confidence:.0%})")
    
    # Test 3: Mixed content
    print(f"\n✓ Test 3: Mixed content (code + documentation)")
    mixed = """
    # Code Example
    def process_data(data):
        return data.strip()
    
    # Documentation
    This function processes input data according to policy guidelines.
    """
    result = classifier.classify(mixed)
    print(f"  Classification: {result.primary_class.value} ({result.confidence:.0%})")
    
    return True


def main():
    print("\n" + "="*70)
    print("ADVANCED DOCUMENT CLASSIFICATION INTEGRATION TEST")
    print("="*70)
    
    tests = [
        ("Classification Pipeline", test_document_classification_pipeline),
        ("Metadata Extraction", test_metadata_extraction),
        ("Confidence Analysis", test_confidence_distribution),
        ("Class Information", test_class_information_retrieval),
        ("Edge Cases", test_edge_cases),
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
    
    # Summary
    print_section("INTEGRATION TEST SUMMARY")
    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name:40} {result}")
    
    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\nTotal: {passed}/{len(results)} test groups passed")
    
    return all(r == "PASS" for _, r in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
