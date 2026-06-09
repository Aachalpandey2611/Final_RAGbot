import { useState, useEffect, useRef, useCallback, FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import { getConversationMessages, createConversation, chatStream } from '../api';
import Sidebar from '../components/Sidebar';

type ResponseMode = 'simple' | 'normal' | 'technical';
type ResponseLength = 'quick' | 'standard' | 'detailed';

interface Message {
  id?: number;
  role: string;
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  originQuery?: string;
}

interface Citation {
  source_index: number;
  chunk_id: number;
  document_id: number;
  filename: string;
  page: number | string;
  distance_score: number | null;
}

function filterUsedCitations(text: string, citations: Citation[]): Citation[] {
  if (!citations || citations.length === 0) return [];
  const usedIndices = new Set<number>();
  const bracketRegex = /\[(.*?)\]/g;
  let bracketMatch;
  while ((bracketMatch = bracketRegex.exec(text)) !== null) {
    const sourceRegex = /Source\s+(\d+)/gi;
    let sourceMatch;
    while ((sourceMatch = sourceRegex.exec(bracketMatch[1])) !== null) {
      usedIndices.add(parseInt(sourceMatch[1], 10));
    }
  }
  return citations.filter((c) => usedIndices.has(c.source_index));
}

function processSources(text: string, citations?: Citation[]) {
  if (!citations || citations.length === 0) return text;
  return text.replace(/\[Source\s+(\d+)\]/gi, (match, numStr) => {
    const num = parseInt(numStr, 10);
    const citation = citations.find(c => c.source_index === num);
    if (citation) {
      return `[📄 ${citation.filename}](#source-${num})`;
    }
    return match;
  });
}

export default function Chat() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [expandedCitation, setExpandedCitation] = useState<number | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [responseMode, setResponseMode] = useState<ResponseMode>('normal');
  const [responseLength, setResponseLength] = useState<ResponseLength>('standard');
  const [regeneratingIdx, setRegeneratingIdx] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isDebugMode, setIsDebugMode] = useState<boolean>(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load messages when conversation changes or streaming finishes
  useEffect(() => {
    if (!conversationId || conversationId < 0) {
      setMessages([]);
      return;
    }
    if (streaming) {
      return; // Prevent wiping optimistic UI during active generation
    }
    getConversationMessages(conversationId)
      .then((data) => {
        setMessages(
          (data.messages || []).map((m: any) => ({ id: m.id, role: m.role, content: m.content }))
        );
      })
      .catch(() => {});
  }, [conversationId, streaming]);

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;

    const query = input.trim();
    setInput('');

    let activeConvId = conversationId;
    if (!activeConvId || activeConvId < 0) {
      try {
        const conv = await createConversation(query.slice(0, 50));
        activeConvId = conv.id;
        setConversationId(conv.id);
      } catch {
        return;
      }
    }

    // Add user message optimistically
    setMessages((prev) => [...prev, { role: 'user', content: query, originQuery: query }]);

    // Add streaming placeholder
    setMessages((prev) => [...prev, { role: 'assistant', content: '', isStreaming: true }]);
    setStreaming(true);
    setCurrentCitations([]);
    setSuggestions([]);

    let citationsAccumulator: any[] = [];
    const abort = chatStream(
      activeConvId!,
      query,
      (event) => {
        if (event.type === 'citations') {
          const received = event.citations || [];
          citationsAccumulator = received;
          setCurrentCitations(received);
        } else if (event.type === 'content') {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.isStreaming) {
              updated[updated.length - 1] = { ...last, content: last.content + event.content };
            }
            return updated;
          });
        } else if (event.type === 'error') {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.isStreaming) {
              updated[updated.length - 1] = {
                ...last,
                content: '⚠️ ' + (event.content || 'An error occurred'),
                isStreaming: false,
              };
            }
            return updated;
          });
        } else if (event.type === 'suggestions') {
          setSuggestions(event.suggestions || []);
        }
      },
      () => {
        setStreaming(false);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.isStreaming) {
            const filteredCitations = filterUsedCitations(last.content, citationsAccumulator);
            setCurrentCitations(filteredCitations);

            updated[updated.length - 1] = {
              ...last,
              isStreaming: false,
              citations: filteredCitations.length > 0 ? filteredCitations : undefined,
            };
          }
          return updated;
        });
      },
      responseMode,
      responseLength
    );

    abortRef.current = abort;
  };

  // Find the user query that produced a given assistant message
  const findOriginQuery = useCallback((assistantIdx: number): string | null => {
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return messages[i].originQuery || messages[i].content;
      }
    }
    return null;
  }, [messages]);

  const handleRegenerate = useCallback(async (assistantIdx: number) => {
    if (streaming || !conversationId) return;

    const query = findOriginQuery(assistantIdx);
    if (!query) return;

    setRegeneratingIdx(assistantIdx);

    // Add new streaming placeholder at end
    setMessages((prev) => [...prev, { role: 'assistant', content: '', isStreaming: true }]);
    setStreaming(true);
    setCurrentCitations([]);

    let citationsAccumulator: any[] = [];
    const abort = chatStream(
      conversationId,
      query,
      (event) => {
        if (event.type === 'citations') {
          citationsAccumulator = event.citations || [];
          setCurrentCitations(citationsAccumulator);
        } else if (event.type === 'content') {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.isStreaming) {
              updated[updated.length - 1] = { ...last, content: last.content + event.content };
            }
            return updated;
          });
        } else if (event.type === 'error') {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.isStreaming) {
              updated[updated.length - 1] = {
                ...last,
                content: '⚠️ ' + (event.content || 'Regeneration failed'),
                isStreaming: false,
              };
            }
            return updated;
          });
        }
      },
      () => {
        setStreaming(false);
        setRegeneratingIdx(null);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.isStreaming) {
            const filteredCitations = filterUsedCitations(last.content, citationsAccumulator);
            setCurrentCitations(filteredCitations);

            updated[updated.length - 1] = {
              ...last,
              isStreaming: false,
              citations: filteredCitations.length > 0 ? filteredCitations : undefined,
            };
          }
          return updated;
        });
      },
      responseMode,
      responseLength
    );

    abortRef.current = abort;
  }, [streaming, conversationId, findOriginQuery, responseMode, responseLength]);

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 2500);
  }, []);

  const handleCopyResponse = useCallback(async (content: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIdx(idx);
      showToast('Response copied successfully', 'success');
      setTimeout(() => setCopiedIdx(null), 2000);
    } catch {
      showToast('Failed to copy — clipboard access denied', 'error');
    }
  }, [showToast]);

  const handleEditMessage = useCallback((content: string, idx: number) => {
    setEditingIdx(idx);
    setInput(content);
    inputRef.current?.focus();
  }, []);

  const handleSelectConversation = (id: number) => {
    setConversationId(id);
    setCurrentCitations([]);
    setExpandedCitation(null);
    setEditingIdx(null);
  };

  const handleNewConversation = (id: number) => {
    setConversationId(id > 0 ? id : null);
    setMessages([]);
    setCurrentCitations([]);
    setEditingIdx(null);
    setSuggestions([]);
  };

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setInput(suggestion);
    setSuggestions([]);
    // Auto-submit after a brief tick so React updates the input
    setTimeout(() => {
      const form = document.querySelector('form');
      if (form) form.requestSubmit();
    }, 50);
  }, []);

  return (
    <div id="chat-page" style={{ display: 'flex', height: '100vh', width: '100%' }}>
      <Sidebar activeId={conversationId} onSelect={handleSelectConversation} onNew={handleNewConversation} />

      {/* Chat area */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
          {messages.length === 0 ? (
            <div style={{
              height: '100%', display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: '12px',
            }}>
              <div style={{
                width: '72px', height: '72px', borderRadius: '20px',
                background: 'linear-gradient(135deg, var(--accent), #00cec9)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '2rem', marginBottom: '8px',
              }}>💬</div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Start a Conversation</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '360px', textAlign: 'center' }}>
                Ask any question about your uploaded documents. The AI will retrieve relevant context and cite its sources.
              </p>
            </div>
          ) : (
            <div style={{ maxWidth: '780px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className="animate-fade-in"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div style={{
                    maxWidth: '85%',
                    padding: '14px 18px',
                    borderRadius: msg.role === 'user'
                      ? '16px 16px 4px 16px'
                      : '16px 16px 16px 4px',
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, var(--accent), #5a4de0)'
                      : 'var(--bg-secondary)',
                    border: msg.role === 'user'
                      ? (editingIdx === i ? '2px solid #f1c40f' : 'none')
                      : '1px solid var(--border-glass)',
                    fontSize: '0.92rem',
                    lineHeight: '1.6',
                    whiteSpace: msg.role === 'user' ? 'pre-wrap' : 'normal',
                    wordBreak: 'break-word',
                    transition: 'border 0.2s ease',
                  }}>
                    {msg.role === 'user' ? (
                      msg.content
                    ) : (
                      <div className="markdown-body">
                        <ReactMarkdown
                          components={{
                            p: ({ node, children }) => <p style={{ marginBottom: '0.75em', lineHeight: 1.6 }}>{children}</p>,
                            a: ({ node, href, children }) => {
                              if (href?.startsWith('#source-')) {
                                return (
                                  <span style={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--accent)',
                                    color: 'var(--accent)',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    margin: '0 4px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                  }}>
                                    {children}
                                  </span>
                                );
                              }
                              return <a href={href} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>{children}</a>;
                            },
                            code: ({ node, inline, className, children, ...props }: any) => {
                              return !inline ? (
                                <pre style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', overflowX: 'auto', marginBottom: '1em' }}>
                                  <code className={className} {...props}>{children}</code>
                                </pre>
                              ) : (
                                <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px' }} {...props}>{children}</code>
                              );
                            },
                          }}
                        >
                          {processSources(msg.content, msg.citations || currentCitations)}
                        </ReactMarkdown>
                        {/* Debug Mode: Show Raw Chunks */}
                        {isDebugMode && (msg.citations || (msg.isStreaming && currentCitations.length > 0)) && (
                          <div style={{
                            marginTop: '16px', padding: '12px', background: 'rgba(0,0,0,0.2)',
                            borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.8rem'
                          }}>
                            <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--warning)' }}>🐞 Debug: Retrieved Chunks Used</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              {(msg.citations || currentCitations).map((c: any, idx: number) => (
                                <div key={idx} style={{ background: 'var(--bg-primary)', padding: '8px', borderRadius: '6px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{c.filename}</span>
                                    <span style={{ color: 'var(--text-muted)' }}>Score: {(c.distance_score !== null && c.distance_score !== undefined) ? (c.distance_score * 100).toFixed(1) : 'N/A'}%</span>
                                  </div>
                                  <div style={{ color: 'var(--text-secondary)' }}>Source Index: {c.source_index}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {msg.isStreaming && !msg.content && (
                      <div style={{ display: 'flex', gap: '6px', padding: '4px 0' }}>
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                      </div>
                    )}
                  </div>

                  {/* Action buttons row */}
                  {!msg.isStreaming && msg.content && (
                    <div style={{
                      display: 'flex',
                      gap: '4px',
                      marginTop: '4px',
                      paddingLeft: msg.role === 'assistant' ? '6px' : '0',
                      paddingRight: msg.role === 'user' ? '6px' : '0',
                    }}>
                      {msg.role === 'assistant' && (
                        <>
                        <button
                          title="Copy Response"
                          onClick={() => handleCopyResponse(msg.content, i)}
                          className="msg-action-btn"
                          style={{
                            background: 'none',
                            border: '1px solid transparent',
                            borderRadius: '8px',
                            padding: '4px 8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.75rem',
                            color: copiedIdx === i ? '#00b894' : 'var(--text-muted)',
                            transition: 'all 0.2s ease',
                          }}
                        >
                          {copiedIdx === i ? (
                            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copied</>
                          ) : (
                            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy</>
                          )}
                        </button>
                        <button
                          title="Regenerate Response"
                          onClick={() => handleRegenerate(i)}
                          className="msg-action-btn"
                          disabled={streaming}
                          style={{
                            background: 'none',
                            border: '1px solid transparent',
                            borderRadius: '8px',
                            padding: '4px 8px',
                            cursor: streaming ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.75rem',
                            color: regeneratingIdx === i ? 'var(--accent)' : 'var(--text-muted)',
                            opacity: streaming ? 0.4 : 1,
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
                          {regeneratingIdx === i ? 'Regenerating...' : 'Regenerate'}
                        </button>
                        </>
                      )}
                      {msg.role === 'user' && (
                        <button
                          title="Edit and Resend"
                          onClick={() => handleEditMessage(msg.content, i)}
                          className="msg-action-btn"
                          disabled={streaming}
                          style={{
                            background: 'none',
                            border: '1px solid transparent',
                            borderRadius: '8px',
                            padding: '4px 8px',
                            cursor: streaming ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.75rem',
                            color: editingIdx === i ? '#f1c40f' : 'var(--text-muted)',
                            opacity: streaming ? 0.4 : 1,
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                          {editingIdx === i ? 'Editing...' : 'Edit'}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Citations section */}
              {currentCitations.length > 0 && !streaming && (
                <div className="animate-fade-in" style={{
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-glass)',
                  borderRadius: 'var(--radius)', padding: '14px 16px',
                }}>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
                    📎 SOURCES
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {currentCitations.map((cit, idx) => (
                      <button
                        key={idx}
                        onClick={() => setExpandedCitation(expandedCitation === idx ? null : idx)}
                        style={{
                          background: expandedCitation === idx ? 'var(--accent)' : 'var(--bg-tertiary)',
                          color: expandedCitation === idx ? '#fff' : 'var(--text-secondary)',
                          border: '1px solid var(--border-glass)',
                          borderRadius: '20px',
                          padding: '5px 14px',
                          fontSize: '0.78rem',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          fontFamily: 'var(--font-sans)',
                        }}
                      >
                        [Source {cit.source_index}] {cit.filename}
                      </button>
                    ))}
                  </div>
                  {expandedCitation !== null && currentCitations[expandedCitation] && (
                    <div className="animate-fade-in" style={{
                      marginTop: '10px', padding: '10px 14px',
                      background: 'var(--bg-primary)', borderRadius: 'var(--radius)',
                      fontSize: '0.82rem', color: 'var(--text-secondary)',
                    }}>
                      <p><strong>File:</strong> {currentCitations[expandedCitation].filename}</p>
                      <p><strong>Page:</strong> {currentCitations[expandedCitation].page}</p>
                      <p><strong>Chunk ID:</strong> {currentCitations[expandedCitation].chunk_id}</p>
                      {currentCitations[expandedCitation].distance_score !== null && (
                        <p><strong>Relevance:</strong> {(currentCitations[expandedCitation].distance_score! * 100).toFixed(1)}%</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Smart Follow-Up Suggestions */}
              {suggestions.length > 0 && !streaming && (
                <div className="animate-fade-in" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  marginTop: '4px',
                }}>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                    💡 Follow-up questions
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {suggestions.map((s, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestionClick(s)}
                        className="suggestion-chip"
                        style={{
                          background: 'var(--bg-tertiary)',
                          color: 'var(--text-secondary)',
                          border: '1px solid var(--border-glass)',
                          borderRadius: '20px',
                          padding: '6px 16px',
                          fontSize: '0.82rem',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          fontFamily: 'var(--font-sans)',
                          textAlign: 'left',
                        }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid var(--border-glass)',
          background: 'var(--bg-secondary)',
        }}>
          {/* Response Style and Length Selectors */}
          <div style={{
            maxWidth: '780px',
            margin: '0 auto 10px',
            display: 'flex',
            gap: '16px',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Response Style:</label>
              <select
                value={responseMode}
                onChange={(e) => setResponseMode(e.target.value as ResponseMode)}
                style={{
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-glass)',
                  borderRadius: '8px',
                  padding: '6px 10px',
                  fontSize: '0.8rem',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="simple">💡 Simple</option>
                <option value="normal">⚖️ Normal</option>
                <option value="technical">⚙️ Technical</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Answer Length:</label>
              <select
                value={responseLength}
                onChange={(e) => setResponseLength(e.target.value as ResponseLength)}
                style={{
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-glass)',
                  borderRadius: '8px',
                  padding: '6px 10px',
                  fontSize: '0.8rem',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="quick">⚡ Quick</option>
                <option value="standard">📏 Standard</option>
                <option value="detailed">🔍 Detailed</option>
              </select>
            </div>
            
            {/* Debug Mode Toggle */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginLeft: 'auto', alignItems: 'flex-end' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Debug Mode</label>
              <button
                type="button"
                onClick={() => setIsDebugMode(!isDebugMode)}
                style={{
                  background: isDebugMode ? 'var(--accent)' : 'var(--bg-primary)',
                  color: isDebugMode ? '#fff' : 'var(--text-primary)',
                  border: '1px solid var(--border-glass)',
                  borderRadius: '8px',
                  padding: '6px 12px',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  fontWeight: 600
                }}
              >
                {isDebugMode ? 'ON 🐞' : 'OFF'}
              </button>
            </div>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(e);
              if (inputRef.current) inputRef.current.style.height = 'auto';
            }}
            style={{
              maxWidth: '780px', margin: '0 auto',
              display: 'flex', gap: '10px', alignItems: 'flex-end',
            }}
          >
            <textarea
              ref={inputRef}
              className="input"
              rows={1}
              placeholder={editingIdx !== null ? 'Edit your question and press Send...' : 'Ask a question about your documents...'}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = e.target.scrollHeight + 'px';
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!streaming && input.trim()) {
                    const form = e.currentTarget.closest('form');
                    if (form) form.requestSubmit();
                  }
                }
              }}
              disabled={streaming}
              style={{
                flex: 1,
                resize: 'none',
                minHeight: '48px',
                maxHeight: '200px',
                padding: '12px 16px',
                borderColor: editingIdx !== null ? '#f1c40f' : undefined,
                boxShadow: editingIdx !== null ? '0 0 0 2px rgba(241,196,15,0.25)' : undefined,
              }}
            />
            {editingIdx !== null && (
              <button
                type="button"
                onClick={() => { setEditingIdx(null); setInput(''); }}
                style={{
                  background: 'none',
                  border: '1px solid var(--border-glass)',
                  borderRadius: 'var(--radius)',
                  padding: '12px 14px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  transition: 'all 0.15s ease',
                }}
                title="Cancel edit"
              >
                ✕
              </button>
            )}
            <button
              id="chat-send"
              type="submit"
              className="btn-primary"
              disabled={streaming || !input.trim()}
              onClick={() => { if (!streaming && input.trim()) setEditingIdx(null); }}
              style={{
                padding: '12px 20px',
                display: 'flex', alignItems: 'center', gap: '6px',
                whiteSpace: 'nowrap',
              }}
            >
              {streaming ? (
                <>
                  <span className="typing-dot" style={{ width: '6px', height: '6px' }} />
                  Thinking
                </>
              ) : editingIdx !== null ? (
                'Resend →'
              ) : (
                'Send →'
              )}
            </button>
          </form>
        </div>
      </main>

      {/* Toast notification */}
      {toast && (
        <div
          className="animate-fade-in"
          style={{
            position: 'fixed',
            bottom: '24px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: toast.type === 'success'
              ? 'linear-gradient(135deg, #00b894, #00cec9)'
              : 'linear-gradient(135deg, #e74c3c, #e84393)',
            color: '#fff',
            padding: '10px 24px',
            borderRadius: '12px',
            fontSize: '0.85rem',
            fontWeight: 600,
            boxShadow: '0 8px 32px rgba(0,0,0,0.35)',
            zIndex: 9999,
            pointerEvents: 'none',
            backdropFilter: 'blur(8px)',
          }}
        >
          {toast.type === 'success' ? '✓' : '✕'} {toast.message}
        </div>
      )}
    </div>
  );
}
