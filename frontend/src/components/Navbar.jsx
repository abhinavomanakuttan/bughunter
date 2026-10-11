import React from 'react';
import { Bug, Activity, ShieldCheck, Cpu, Terminal, History, PlusCircle, Sparkles } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, health, currentScanId }) {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 32px',
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(10, 15, 26, 0.85)',
      backdropFilter: 'blur(20px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '42px',
          height: '42px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)',
          border: '1px solid var(--border-glow)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-glow)',
        }}>
          <Bug size={24} color="#06b6d4" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(to right, #ffffff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              BugHunter
            </h1>
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '999px',
              background: 'rgba(6, 182, 212, 0.15)',
              color: '#22d3ee',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}>
              Autonomous AI QA
            </span>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Observe · Plan · Act · Verify QA Agent
          </p>
        </div>
      </div>

      {/* Tabs */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.6)', padding: '4px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
        <button
          id="nav-launchpad-btn"
          onClick={() => setActiveTab('launchpad')}
          className={`btn ${activeTab === 'launchpad' ? 'btn-primary' : 'btn-outline'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <PlusCircle size={16} />
          New Scan
        </button>

        <button
          id="nav-monitor-btn"
          onClick={() => setActiveTab('monitor')}
          className={`btn ${activeTab === 'monitor' ? 'btn-primary' : 'btn-outline'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem', position: 'relative' }}
        >
          <Activity size={16} />
          Live Radar
          {currentScanId && (
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#10b981',
              boxShadow: '0 0 8px #10b981',
              position: 'absolute',
              top: '8px',
              right: '8px',
            }} />
          )}
        </button>

        <button
          id="nav-findings-btn"
          onClick={() => setActiveTab('findings')}
          className={`btn ${activeTab === 'findings' ? 'btn-primary' : 'btn-outline'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <Bug size={16} />
          Bug Explorer
        </button>

        <button
          id="nav-history-btn"
          onClick={() => setActiveTab('history')}
          className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-outline'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <History size={16} />
          Scan History
        </button>
      </nav>

      {/* Status Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          borderRadius: '20px',
          background: health ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
          border: `1px solid ${health ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          fontSize: '0.78rem',
          fontWeight: 600,
          color: health ? '#34d399' : '#f87171',
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: health ? '#10b981' : '#f43f5e',
          }} />
          {health ? 'API Online' : 'Connecting...'}
        </div>

        {health?.demo_mode && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '6px 12px',
            borderRadius: '20px',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            fontSize: '0.78rem',
            fontWeight: 600,
            color: '#fbbf24',
          }}>
            <ShieldCheck size={14} />
            Demo Mode Active
          </div>
        )}

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          padding: '6px 12px',
          borderRadius: '20px',
          background: 'rgba(139, 92, 246, 0.12)',
          border: '1px solid rgba(139, 92, 246, 0.35)',
          fontSize: '0.78rem',
          fontWeight: 600,
          color: '#c084fc',
        }}>
          <Cpu size={14} />
          {health?.llm_provider ? `LLM: ${health.llm_provider}` : 'LLM Engine'}
        </div>
      </div>
    </header>
  );
}
