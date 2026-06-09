import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDocument, chunkDocument, embedDocument, listDocuments, deleteDocument } from '../api';
import { useAuth } from '../AuthContext';
import { useEffect } from 'react';

interface DocInfo {
  id: number;
  original_filename: string;
  file_size: number;
  uploaded_at: string;
}

type UploadStage = 'idle' | 'uploading' | 'chunking' | 'embedding' | 'done' | 'error';

export default function Upload() {
  const [stage, setStage] = useState<UploadStage>('idle');
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState('');
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [previewDoc, setPreviewDoc] = useState<DocInfo | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const MAX_FILES = 500;
  const isLimitReached = docs.length >= MAX_FILES;

  useEffect(() => {
    listDocuments()
      .then((data) => setDocs(data.documents || data))
      .catch(() => {});
  }, [stage]);

  const processFile = useCallback(async (file: File) => {
    // Check limit
    if (isLimitReached) {
      setError(`Upload limit of ${MAX_FILES} files reached. Delete older files to upload new ones.`);
      return;
    }

    // Skip macOS AppleDouble hidden files and generic hidden files
    if (file.name.startsWith('.') || file.name.startsWith('._')) {
      console.log(`Skipping hidden file: ${file.name}`);
      setError(`Cannot upload hidden files (${file.name})`);
      return;
    }
    
    setFileName(file.name);
    setError('');
      let docId: number | null = null;
      try {
        setStage('uploading');
        setProgress('Uploading document...');
        const doc = await uploadDocument(file);
        docId = doc.id;

        setStage('chunking');
        setProgress('Splitting into chunks...');
        await chunkDocument(doc.id);

        setStage('embedding');
        setProgress('Generating embeddings...');
        await embedDocument(doc.id);

        setStage('done');
        setProgress('Document processed successfully!');
        setTimeout(() => setStage('idle'), 3000);
      } catch (err: any) {
        setStage('error');
        setError(err.message || 'Processing failed');
        setTimeout(() => setStage('idle'), 4000);
        // Rollback uploaded document if chunking/embedding fails
        if (docId) {
          try {
            await deleteDocument(docId);
            listDocuments().then((data) => setDocs(data.documents || data)).catch(() => {});
          } catch (e) {
            console.error("Rollback failed", e);
          }
        }
      }
  }, [isLimitReached, MAX_FILES]);

  const getFilesFromDataTransfer = async (items: DataTransferItemList): Promise<File[]> => {
    const files: File[] = [];
    const readEntry = async (entry: any) => {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve) => entry.file(resolve));
        files.push(file);
      } else if (entry.isDirectory) {
        const reader = entry.createReader();
        const readEntriesPromise = () => new Promise<any[]>((resolve, reject) => reader.readEntries(resolve, reject));
        
        let allEntries: any[] = [];
        let entries = await readEntriesPromise();
        while (entries.length > 0) {
          allEntries = allEntries.concat(entries);
          entries = await readEntriesPromise();
        }
        
        for (const child of allEntries) {
          await readEntry(child);
        }
      }
    };

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry?.();
        if (entry) {
          await readEntry(entry);
        } else {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
    }
    return files;
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    let files: File[] = [];
    if (e.dataTransfer.items) {
      files = await getFilesFromDataTransfer(e.dataTransfer.items);
    } else {
      files = Array.from(e.dataTransfer.files);
    }
    
    // Filter hidden files
    files = files.filter(f => !f.name.startsWith('.'));
    
    for (const file of files) {
      await processFile(file);
    }
  };

  const stageColors: Record<UploadStage, string> = {
    idle: 'var(--text-muted)',
    uploading: 'var(--accent)',
    chunking: 'var(--warning)',
    embedding: '#00cec9',
    done: 'var(--success)',
    error: 'var(--danger)',
  };

  return (
    <div
      id="upload-page"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f0f13 0%, #1a1a2e 50%, #16213e 100%)',
        display: 'flex', flexDirection: 'column',
      }}
    >
      {/* Top bar */}
      <header style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '16px 24px', borderBottom: '1px solid var(--border-glass)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: 'linear-gradient(135deg, var(--accent), #00cec9)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem',
          }}>💬</div>
          <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>DocChat</span>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-ghost" onClick={() => navigate('/')}>← Back to Chat</button>
          <button className="btn-ghost" onClick={logout}>Logout</button>
        </div>
      </header>

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '2rem', gap: '2rem',
      }}>
        <div style={{ textAlign: 'center', maxWidth: '520px' }}>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px' }}>Upload Documents</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Drop a PDF, DOCX, TXT, MD, CSV, ZIP, Excel, or image file to add it to your knowledge base.
            The system will automatically chunk and embed the content.
          </p>
        </div>

        {/* Drop zone */}
        <div
          id="upload-dropzone"
          className={`glass animate-fade-in ${isLimitReached ? 'disabled' : ''}`}
          onDragOver={(e) => { e.preventDefault(); if (!isLimitReached) setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { if (!isLimitReached) handleDrop(e); }}
          onClick={() => stage === 'idle' && !isLimitReached && fileRef.current?.click()}
          style={{
            width: '100%', maxWidth: '520px', minHeight: '200px',
            borderRadius: 'var(--radius-lg)', padding: '40px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            cursor: stage === 'idle' && !isLimitReached ? 'pointer' : 'default',
            borderColor: dragOver ? 'var(--accent)' : undefined,
            borderWidth: dragOver ? '2px' : undefined,
            opacity: isLimitReached ? 0.6 : 1,
            transition: 'all 0.2s ease',
          }}
        >
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt,.csv,.md,.png,.jpg,.jpeg,.xls,.xlsx,.zip"
            style={{ display: 'block', margin: '20px auto', padding: '10px' }}
            onChange={async (e) => {
              if (e.target.files && e.target.files.length > 0) {
                const files = Array.from(e.target.files);
                for (const f of files) {
                  await processFile(f);
                }
                // Reset input value so same file can be selected again
                e.target.value = '';
              }
            }}
          />
          <input
            ref={folderRef}
            type="file"
            // @ts-ignore - webkitdirectory is a non-standard attribute but widely supported
            webkitdirectory="true"
            directory="true"
            multiple
            style={{ display: 'none' }}
            onChange={async (e) => {
              if (e.target.files) {
                const files = Array.from(e.target.files);
                for (const f of files) {
                  // Skip hidden files/directories like .git or .DS_Store
                  if (!f.name.startsWith('.') && !f.webkitRelativePath.includes('/.')) {
                    await processFile(f);
                  }
                }
              }
            }}
          />

          {stage === 'idle' ? (
            <>
              <div style={{ fontSize: '3rem', marginBottom: '12px', opacity: 0.6 }}>📄</div>
              {isLimitReached ? (
                <p style={{ color: 'var(--danger)', fontSize: '0.95rem', fontWeight: 600 }}>
                  Upload limit reached. Please delete existing documents to free up space.
                </p>
              ) : (
                <>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                    Drag & drop files/folders here, or{' '}
                    <span style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}>browse files</span>
                    {' '}or{' '}
                    <span style={{ color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); folderRef.current?.click(); }}>browse folders</span>
                  </p>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '6px' }}>
                    PDF, DOCX, TXT, MD, CSV, ZIP, XLS, PNG, JPG • Max 10MB
                  </p>
                </>
              )}
            </>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: '48px', height: '48px', borderRadius: '50%',
                background: `${stageColors[stage]}22`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px', fontSize: '1.4rem',
              }}>
                {stage === 'done' ? '✅' : stage === 'error' ? '❌' : '⏳'}
              </div>
              <p style={{ fontWeight: 600, marginBottom: '6px' }}>{fileName}</p>
              <p style={{ color: stageColors[stage], fontSize: '0.9rem' }}>
                {error || progress}
              </p>
              {(stage === 'done' || stage === 'error') && (
                <button
                  className="btn-primary"
                  style={{ marginTop: '16px' }}
                  onClick={(e) => { e.stopPropagation(); setStage('idle'); setError(''); }}
                >
                  Upload Another
                </button>
              )}
            </div>
          )}
        </div>

        {/* Document list */}
        {docs.length > 0 && (
          <div className="glass animate-fade-in" style={{
            width: '100%', maxWidth: '520px', borderRadius: 'var(--radius-lg)', padding: '20px',
            display: 'flex', flexDirection: 'column', gap: '12px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                📚 Uploaded Documents ({docs.length}/{MAX_FILES} used)
              </h3>
            </div>
            
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: '8px',
                border: '1px solid var(--border-glass)', background: 'var(--bg-primary)',
                color: 'var(--text-primary)', outline: 'none', fontSize: '0.9rem'
              }}
            />

            <div style={{ 
              display: 'flex', flexDirection: 'column', gap: '8px', 
              maxHeight: '350px', overflowY: 'auto', paddingRight: '4px' 
            }}>
              {docs.filter(doc => doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase())).map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', borderRadius: 'var(--radius)',
                    background: 'var(--bg-secondary)', fontSize: '0.85rem',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
                    <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {doc.original_filename}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {(doc.file_size / 1024).toFixed(1)} KB • {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '8px', marginLeft: '12px' }}>
                    <button
                      onClick={() => setPreviewDoc(doc)}
                      style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '1rem' }}
                      title="View Details"
                    >
                      👁️
                    </button>
                    <button
                      onClick={async () => {
                        if (confirm(`Are you sure you want to delete ${doc.original_filename}?`)) {
                          try {
                            await deleteDocument(doc.id);
                            setDocs(docs.filter(d => d.id !== doc.id));
                          } catch (e) {
                            alert("Failed to delete document");
                          }
                        }
                      }}
                      style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '1rem' }}
                      title="Delete Document"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
              {docs.filter(doc => doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase())).length === 0 && (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.85rem', padding: '12px 0' }}>No documents match your search.</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Document Details Modal */}
      {previewDoc && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }} onClick={() => setPreviewDoc(null)}>
          <div className="glass" style={{
            width: '90%', maxWidth: '500px', padding: '24px', borderRadius: 'var(--radius-lg)',
            display: 'flex', flexDirection: 'column', gap: '16px'
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Document Details</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem' }}>
              <p><strong>Name:</strong> {previewDoc.original_filename}</p>
              <p><strong>Size:</strong> {(previewDoc.file_size / 1024).toFixed(2)} KB</p>
              <p><strong>Uploaded:</strong> {new Date(previewDoc.uploaded_at).toLocaleString()}</p>
              <p><strong>Status:</strong> Processed & Indexed in Vector Store ✅</p>
            </div>
            <button className="btn-ghost" onClick={() => setPreviewDoc(null)} style={{ alignSelf: 'flex-end', marginTop: '8px' }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
