#!/usr/bin/env python3
"""
Comprehensive tests for the Document Classification service
"""

import sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

# Load classifier module directly
classifier_path = Path(__file__).parent / 'app' / 'services' / 'classification.py'
spec = spec_from_file_location("classification", classifier_path)
classification_module = module_from_spec(spec)
spec.loader.exec_module(classification_module)

DocumentClassifier = classification_module.DocumentClassifier
DocumentClass = classification_module.DocumentClass


def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")


def test_policy_classification():
    """Test classification of policy documents"""
    print_section("TEST 1: Policy Document Classification")
    
    policy_text = """
    COMPANY POLICY DOCUMENT
    Effective Date: January 1, 2024
    
    1. Introduction
    This policy is established to ensure compliance with organizational standards
    and regulatory requirements.
    
    2. Policy Guidelines
    All employees shall adhere to the following guidelines:
    - Remote work is approved based on manager discretion
    - Employees must follow company security protocols
    - All work products must be approved before publication
    
    3. Compliance
    Non-compliance with this policy may result in disciplinary action in accordance with
    company guidelines.
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(policy_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Tags: {', '.join(result.tags[:3])}")
    
    print(f"\n  All class scores:")
    for class_name, score in sorted(result.class_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {class_name.value:25} {score:6.1%}")
    
    assert result.primary_class == DocumentClass.POLICIES, "Should classify as Policies"
    assert result.confidence >= 0.5, f"Confidence should be >= 0.5, got {result.confidence}"
    
    return True


def test_technical_document_classification():
    """Test classification of technical documents"""
    print_section("TEST 2: Technical Document Classification")
    
    tech_doc = """
    # System Architecture Specification
    
    ## 1. Overview
    This document describes the technical architecture of the microservices platform.
    
    ## 2. Components
    
    ### 2.1 API Gateway
    The API gateway handles all incoming HTTP requests and routes them to appropriate services.
    
    ### 2.2 Message Queue
    Redis-based message queue for asynchronous task processing.
    Specification: Redis 6.0+ with cluster mode enabled.
    
    ## 3. Database Schema
    
    ### Users Table
    - id (UUID primary key)
    - username (VARCHAR(255) unique)
    - email_hash (VARCHAR(64))
    - created_at (TIMESTAMP)
    
    ## 4. API Endpoints
    
    - GET /api/v1/users - List users
    - POST /api/v1/users - Create user
    - GET /api/v1/users/{id} - Get user
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(tech_doc)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Word count: {result.metadata['text_statistics']['total_words']}")
    print(f"  Tags: {', '.join(result.tags[:4])}")
    
    assert result.primary_class == DocumentClass.TECHNICAL_DOCUMENTS, "Should classify as Technical Documents"
    
    return True


def test_source_code_classification():
    """Test classification of source code"""
    print_section("TEST 3: Source Code Classification")
    
    code_text = """
    # User Service Implementation
    
    from typing import Optional, List
    from sqlalchemy.orm import Session
    
    class UserService:
        def __init__(self, db: Session):
            self.db = db
        
        def create_user(self, username: str, email: str) -> User:
            '''Create a new user'''
            user = User(username=username, email=email)
            self.db.add(user)
            self.db.commit()
            return user
        
        def get_user(self, user_id: int) -> Optional[User]:
            '''Retrieve user by ID'''
            return self.db.query(User).filter(User.id == user_id).first()
        
        def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
            '''List users with pagination'''
            return self.db.query(User).offset(skip).limit(limit).all()
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(code_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Has code markers: {result.tags}")
    
    assert result.primary_class == DocumentClass.SOURCE_CODE, "Should classify as Source Code"
    assert "code_content" in result.tags, "Should have code_content tag"
    
    return True


def test_email_classification():
    """Test classification of email messages"""
    print_section("TEST 4: Email Classification")
    
    email_text = """
    Subject: Project Status Update - Q2 2024
    
    Dear Team,
    
    I wanted to follow up on our project status. Please see the summary below:
    
    - Milestone 1: 95% complete, on track for next week
    - Milestone 2: 60% complete, may need additional resources
    - Bug fixes: 25 critical issues resolved
    
    Action Items:
    - Review resource allocation by EOD Friday (URGENT)
    - Submit project risks assessment
    - Schedule team retrospective
    
    Let me know if you have any questions.
    
    Thanks,
    Project Manager
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(email_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Email indicators found: {result.tags}")
    
    assert result.primary_class == DocumentClass.EMAILS, "Should classify as Email"
    
    return True


def test_contract_classification():
    """Test classification of contracts"""
    print_section("TEST 5: Contract/Legal Document Classification")
    
    contract_text = """
    SOFTWARE DEVELOPMENT AGREEMENT
    
    THIS AGREEMENT is entered into as of the 1st day of January, 2024, 
    between ABC Corporation ("Client") and XYZ Development LLC ("Developer").
    
    WHEREAS, the Developer agrees to provide software development services;
    
    NOW, THEREFORE, in consideration of the mutual covenants and agreements herein contained,
    the parties hereby agree as follows:
    
    1. SCOPE OF WORK
    The Developer shall deliver a web-based application with the following specifications:
    - Multi-tenant architecture
    - RESTful API with OAuth 2.0 authentication
    - PostgreSQL database backend
    
    2. PAYMENT TERMS
    Client shall pay Developer $50,000 in three equal installments:
    - 30% upon contract execution
    - 30% upon delivery of core features
    - 40% upon final delivery and acceptance
    
    3. INTELLECTUAL PROPERTY
    All work product created under this Agreement shall be owned by the Client,
    notwithstanding any pre-existing materials or third-party components.
    
    4. LIMITATION OF LIABILITY
    In no event shall either party be liable for indirect, incidental, or consequential damages.
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(contract_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Has legal terms: {result.tags}")
    
    assert result.primary_class == DocumentClass.CONTRACTS, "Should classify as Contracts"
    
    return True


def test_meeting_notes_classification():
    """Test classification of meeting notes"""
    print_section("TEST 6: Meeting Notes Classification")
    
    meeting_text = """
    MEETING MINUTES
    Date: June 1, 2024
    Time: 2:00 PM - 3:30 PM
    Location: Conference Room B
    
    Attendees:
    - John Smith (Product Manager)
    - Sarah Johnson (Engineering Lead)
    - Mike Chen (Design)
    - Lisa Rodriguez (QA)
    
    Agenda Items:
    
    1. Q2 Release Status
       - Current: 85% complete
       - Discussed: Possible delay due to API integration issues
    
    2. New Feature Requests
       - Dark mode implementation
       - Export to PDF functionality
       - Mobile app optimization
    
    Action Items:
    1. John: Resolve API integration issues (Due: June 5)
    2. Sarah: Provide timeline estimate for dark mode (Due: June 3)
    3. Lisa: Begin regression testing (Start: June 2)
    4. Mike: Create design mockups for new features (Due: June 6)
    
    Next Meeting: June 8, 2024 at 2:00 PM
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(meeting_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    
    assert result.primary_class == DocumentClass.MEETING_NOTES, "Should classify as Meeting Notes"
    
    return True


def test_manual_classification():
    """Test classification of user manuals"""
    print_section("TEST 7: User Manual Classification")
    
    manual_text = """
    USER GUIDE - Document Management System v3.0
    
    Chapter 1: Getting Started
    
    1.1 Installation
    To use the system, follow these steps:
    
    Step 1: Download the installer from www.example.com
    Step 2: Run the installer executable
    Step 3: Follow the on-screen instructions
    Step 4: Enter your license key when prompted
    
    1.2 First Login
    
    After installation, here's how to log in:
    1. Open the application
    2. Click "Login"
    3. Enter your username and password
    4. Click "Sign In"
    
    Chapter 2: Basic Operations
    
    2.1 Creating a New Document
    
    To create a new document:
    1. Click File menu
    2. Select "New"
    3. Choose document type from the dropdown
    4. Enter document name
    5. Click Create
    
    2.2 Uploading Files
    
    Follow these steps to upload a file:
    Step 1: Navigate to the Upload section
    Step 2: Click "Choose File"
    Step 3: Select file from your computer
    Step 4: Click "Upload"
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(manual_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Document structure: {result.metadata.get('text_statistics', {})}")
    
    assert result.primary_class == DocumentClass.MANUALS, "Should classify as Manuals"
    
    return True


def test_procedure_classification():
    """Test classification of procedures"""
    print_section("TEST 8: Procedure/Process Document Classification")
    
    procedure_text = """
    INCIDENT RESPONSE PROCEDURE
    
    Purpose: To establish a standardized process for responding to system incidents
    
    Scope: All IT staff and operations teams
    
    Procedure Steps:
    
    Step 1: Incident Detection
    - Monitor alerts and notifications
    - First responder acknowledges incident
    - Assess severity level (Critical, High, Medium, Low)
    
    Step 2: Initial Response
    - Create incident ticket in tracking system
    - Notify incident manager
    - Begin data collection
    
    Step 3: Investigation
    - Analyze logs and system state
    - Identify root cause
    - Document findings
    
    Step 4: Resolution
    - Implement fixes
    - Test in staging environment
    - Deploy to production
    
    Step 5: Verification
    - Confirm incident resolved
    - Monitor for 24 hours
    - Close ticket
    
    Step 6: Post-Incident Review
    - Schedule review meeting
    - Document lessons learned
    - Update procedures if needed
    """
    
    classifier = DocumentClassifier(use_embeddings=False)
    result = classifier.classify(procedure_text)
    
    print(f"✓ Document classified as: {result.primary_class.value}")
    print(f"  Confidence: {result.confidence:.0%}")
    
    assert result.primary_class == DocumentClass.PROCEDURES, "Should classify as Procedures"
    
    return True


def test_batch_classification():
    """Test batch classification of multiple documents"""
    print_section("TEST 9: Batch Classification")
    
    documents = [
        ("def hello_world():\n    print('Hello')", "code1.py"),
        ("This is an email. Dear Sir, Please review. Thanks.", "email1.txt"),
        ("Meeting Notes: Discussed project status.", "notes1.txt"),
    ]
    
    classifier = DocumentClassifier(use_embeddings=False)
    results = classifier.classify_batch(documents)
    
    print(f"✓ Classified {len(results)} documents")
    for i, result in enumerate(results):
        doc_text, doc_id = documents[i]
        print(f"\n  Document {i+1}: {doc_id}")
        print(f"    Class: {result.primary_class.value}")
        print(f"    Confidence: {result.confidence:.0%}")
    
    assert len(results) == 3, "Should classify all 3 documents"
    assert results[0].primary_class == DocumentClass.SOURCE_CODE
    assert results[1].primary_class == DocumentClass.EMAILS
    assert results[2].primary_class == DocumentClass.MEETING_NOTES
    
    return True


def test_confidence_scores():
    """Test confidence score calculation"""
    print_section("TEST 10: Confidence Score Validation")
    
    test_docs = [
        ("def foo():\n    return 42", DocumentClass.SOURCE_CODE, 0.6),  # Clear code
        ("I agree to the terms and conditions hereby", DocumentClass.CONTRACTS, 0.5),  # Partial match
        ("Meeting agenda: 1. Updates 2. Planning", DocumentClass.MEETING_NOTES, 0.5),  # Ambiguous
    ]
    
    classifier = DocumentClassifier(use_embeddings=False)
    
    print(f"✓ Testing confidence scoring:")
    for text, expected_class, min_conf in test_docs:
        result = classifier.classify(text)
        print(f"\n  Text: '{text[:40]}...'")
        print(f"  Expected: {expected_class.value}")
        print(f"  Predicted: {result.primary_class.value} ({result.confidence:.0%})")
        
        # Check confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range: {result.confidence}"
    
    return True


def main():
    print("\n" + "="*70)
    print("DOCUMENT CLASSIFICATION SERVICE - TEST SUITE")
    print("="*70)
    
    tests = [
        ("Policy Document", test_policy_classification),
        ("Technical Document", test_technical_document_classification),
        ("Source Code", test_source_code_classification),
        ("Email Message", test_email_classification),
        ("Contract/Legal", test_contract_classification),
        ("Meeting Notes", test_meeting_notes_classification),
        ("User Manual", test_manual_classification),
        ("Procedure/Process", test_procedure_classification),
        ("Batch Classification", test_batch_classification),
        ("Confidence Scores", test_confidence_scores),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS" if result else "FAIL"))
        except AssertionError as e:
            results.append((name, f"FAIL: {str(e)[:40]}"))
        except Exception as e:
            results.append((name, f"ERROR: {str(e)[:40]}"))
            import traceback
            traceback.print_exc()
    
    # Summary
    print_section("TEST SUMMARY")
    for name, result in results:
        status = "✓" if result == "PASS" else "✗"
        print(f"{status} {name:30} {result}")
    
    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    return all(r == "PASS" for _, r in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
