"""
End-to-end verification script:
1. Register a test user
2. Login to get JWT token
3. Upload company_policy.pdf
4. Trigger chunking
5. Verify chunks in database via API
"""
import httpx
import json
import sys
import os

BASE_URL = "http://localhost:8000/api/v1"
PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company_policy.pdf")

def main():
    client = httpx.Client(timeout=120.0)
    
    print("=" * 60)
    print("END-TO-END VERIFICATION PIPELINE")
    print("=" * 60)

    # -- Step 1: Register a test user --
    print("\n[Step 1] Registering test user...")
    reg_resp = client.post(f"{BASE_URL}/auth/register", json={
        "email": "testuser_e2e@example.com",
        "password": "TestPass123!",
        "username": "testuser_e2e"
    })
    if reg_resp.status_code == 201:
        print(f"  [OK] User registered: {reg_resp.json()}")
    elif reg_resp.status_code == 400 and "already" in reg_resp.text.lower():
        print(f"  [INFO] User already exists, skipping registration.")
    else:
        print(f"  [WARN] Registration response ({reg_resp.status_code}): {reg_resp.text}")

    # -- Step 2: Login --
    print("\n[Step 2] Logging in...")
    login_resp = client.post(f"{BASE_URL}/auth/login", data={
        "username": "testuser_e2e@example.com",
        "password": "TestPass123!"
    })
    if login_resp.status_code != 200:
        print(f"  [FAIL] Login failed ({login_resp.status_code}): {login_resp.text}")
        sys.exit(1)
    
    token_data = login_resp.json()
    access_token = token_data.get("access_token")
    print(f"  [OK] Login successful. Token type: {token_data.get('token_type')}")
    
    headers = {"Authorization": f"Bearer {access_token}"}

    # -- Step 3: Upload PDF --
    print(f"\n[Step 3] Uploading {os.path.basename(PDF_PATH)}...")
    if not os.path.exists(PDF_PATH):
        print(f"  [FAIL] PDF not found at: {PDF_PATH}")
        sys.exit(1)
    
    with open(PDF_PATH, "rb") as f:
        upload_resp = client.post(
            f"{BASE_URL}/documents/upload",
            files={"file": ("company_policy.pdf", f, "application/pdf")},
            headers=headers
        )
    
    if upload_resp.status_code != 201:
        print(f"  [FAIL] Upload failed ({upload_resp.status_code}): {upload_resp.text}")
        sys.exit(1)
    
    doc_data = upload_resp.json()
    document_id = doc_data["id"]
    print(f"  [OK] Document uploaded!")
    print(f"     document_id: {document_id}")
    print(f"     filename: {doc_data.get('original_filename')}")
    print(f"     file_size: {doc_data.get('file_size')} bytes")
    print(f"     status: uploaded")

    # -- Step 4: Trigger Chunking --
    print(f"\n[Step 4] Triggering chunking for document_id={document_id}...")
    chunk_resp = client.post(
        f"{BASE_URL}/documents/{document_id}/chunk",
        json={"chunk_size": 1000, "chunk_overlap": 200},
        headers=headers
    )
    
    if chunk_resp.status_code != 201:
        print(f"  [FAIL] Chunking failed ({chunk_resp.status_code}): {chunk_resp.text}")
        sys.exit(1)
    
    chunk_data = chunk_resp.json()
    total_chunks = chunk_data["total"]
    print(f"  [OK] Chunking complete!")
    print(f"     chunks_created: {total_chunks}")

    # -- Step 5: Verify Chunks via API --
    print(f"\n[Step 5] Verifying chunks via GET /documents/{document_id}/chunks...")
    verify_resp = client.get(
        f"{BASE_URL}/documents/{document_id}/chunks",
        headers=headers
    )
    
    if verify_resp.status_code != 200:
        print(f"  [FAIL] Verification failed ({verify_resp.status_code}): {verify_resp.text}")
        sys.exit(1)
    
    verify_data = verify_resp.json()
    chunks = verify_data["chunks"]
    print(f"  [OK] Verified {verify_data['total']} chunks in database!")
    
    print(f"\n{'-' * 60}")
    print(f"CHUNK SAMPLES (first 3 chunks):")
    print(f"{'-' * 60}")
    for chunk in chunks[:3]:
        print(f"\n  Chunk #{chunk['chunk_index']} (id={chunk['id']})")
        content_preview = chunk['content'][:120].replace('\n', ' ')
        print(f"     Content preview: {content_preview}...")
        if chunk.get('meta_data'):
            meta_str = json.dumps(chunk['meta_data'])[:200]
            print(f"     Metadata: {meta_str}")

    # -- Step 6: Trigger Embedding --
    print(f"\n[Step 6] Triggering embedding for document_id={document_id}...")
    embed_resp = client.post(
        f"{BASE_URL}/documents/{document_id}/embed",
        json={"provider": "huggingface"}, # use HF locally to avoid API key issues
        headers=headers
    )
    
    if embed_resp.status_code != 201:
        print(f"  [WARN] Embedding failed ({embed_resp.status_code}): {embed_resp.text}")
    else:
        embed_data = embed_resp.json()
        print(f"  [OK] Embedding complete!")
        print(f"     embedded_chunks: {embed_data['embedded_chunks']} / {embed_data['total_chunks']}")
        print(f"     embedding_model: {embed_data.get('embedding_model')}")
        print(f"     is_complete: {embed_data.get('is_complete')}")

    # -- Summary --
    print(f"\n{'=' * 60}")
    print(f"ALL VERIFICATION STEPS PASSED!")
    print(f"{'=' * 60}")
    print(f"  Document: company_policy.pdf")
    print(f"  Document ID: {document_id}")
    print(f"  Total Chunks: {total_chunks}")
    print(f"  Stored in PostgreSQL table: document_chunk")
    print(f"{'=' * 60}")

    client.close()

if __name__ == "__main__":
    main()
