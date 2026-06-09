import { useEffect, useState } from 'react';
import { listConversations, createConversation, deleteConversation } from '../api';
import { useAuth } from '../AuthContext';

interface Conversation {
  id: number;
  title: string;
  updated_at: string;
}

interface SidebarProps {
  activeId: number | null;
  onSelect: (id: number) => void;
  onNew: (id: number) => void;
}

export default function Sidebar({ activeId, onSelect, onNew }: SidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const { logout } = useAuth();

  const load = async () => {
    try {
      const data = await listConversations();
      setConversations(data.conversations || []);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [activeId]);

  const handleNew = async () => {
    try {
      const conv = await createConversation();
      setConversations((prev) => [conv, ...prev]);
      onNew(conv.id);
    } catch { /* ignore */ }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) onNew(-1); // signal to create new
    } catch { /* ignore */ }
  };

  return (
    <aside
      id="sidebar"
      style={{
        width: '280px', minWidth: '280px',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-glass)',
        display: 'flex', flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Header */}
      <div style={{
        padding: '16px', display: 'flex', alignItems: 'center', gap: '10px',
        borderBottom: '1px solid var(--border-glass)',
      }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '10px',
          background: 'linear-gradient(135deg, var(--accent), #00cec9)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem',
        }}>💬</div>
        <span style={{ fontWeight: 700, fontSize: '1rem' }}>DocChat</span>
      </div>

      {/* New chat button */}
      <div style={{ padding: '12px' }}>
        <button
          id="new-chat-btn"
          className="btn-primary"
          onClick={handleNew}
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
        >
          <span style={{ fontSize: '1.1rem' }}>+</span> New Chat
        </button>
      </div>

      {/* Conversation list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 12px' }}>
        {loading ? (
          <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '20px 0' }}>
            Loading...
          </p>
        ) : conversations.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '20px 0' }}>
            No conversations yet
          </p>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className="animate-slide-left"
              onClick={() => onSelect(conv.id)}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius)',
                cursor: 'pointer',
                marginBottom: '4px',
                background: activeId === conv.id ? 'var(--bg-tertiary)' : 'transparent',
                borderLeft: activeId === conv.id ? '3px solid var(--accent)' : '3px solid transparent',
                transition: 'all 0.15s ease',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}
              onMouseEnter={(e) => {
                if (activeId !== conv.id) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              }}
              onMouseLeave={(e) => {
                if (activeId !== conv.id) e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ overflow: 'hidden', flex: 1 }}>
                <p style={{
                  fontSize: '0.85rem', fontWeight: activeId === conv.id ? 600 : 400,
                  color: activeId === conv.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {conv.title}
                </p>
              </div>
              <button
                onClick={(e) => handleDelete(e, conv.id)}
                style={{
                  background: 'none', border: 'none', color: 'var(--text-muted)',
                  cursor: 'pointer', padding: '4px', fontSize: '0.8rem', flexShrink: 0,
                  opacity: 0.4, transition: 'opacity 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = 'var(--danger)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.4'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                title="Delete conversation"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>

      {/* Bottom nav */}
      <div style={{
        padding: '12px', borderTop: '1px solid var(--border-glass)',
        display: 'flex', flexDirection: 'column', gap: '6px',
      }}>
        <button className="btn-ghost" onClick={() => window.location.href = '/upload'} style={{ width: '100%', textAlign: 'left' }}>
          📄 Upload Documents
        </button>
        <button className="btn-ghost" onClick={logout} style={{ width: '100%', textAlign: 'left' }}>
          🚪 Logout
        </button>
      </div>
    </aside>
  );
}
