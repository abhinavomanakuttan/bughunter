import React, { useState, useEffect, useRef } from 'react';
import { Activity, ShieldAlert, FileText, CheckCircle, AlertCircle, Compass, Zap, Eye, Terminal, Clock, ExternalLink, ArrowRight } from 'lucide-react';
import { subscribeScanEvents, getScan } from '../api/client';

export default function LiveScanMonitor({ scanId, targetUrl, onViewFindings }) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('running');
  const [pagesCrawled, setPagesCrawled] = useState(0);
  const [actionsTaken, setActionsTaken] = useState(0);
  const [findingsCount, setFindingsCount] = useState(0);
  const [wcagScore, setWcagScore] = useState(null);
  const [currentPhase, setCurrentPhase] = useState('Initializing...');
  const [scanData, setScanData] = useState(null);
  const terminalEndRef = useRef(null);

  // Auto-scroll terminal log
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  useEffect(() => {
    if (!scanId) return;

    // Fetch initial scan state
    getScan(scanId).then((data) => {
      setScanData(data);
      if (data.status) setStatus(data.status);
      if (data.pages_crawled) setPagesCrawled(data.pages_crawled);
      if (data.findings_count) setFindingsCount(data.findings_count);
      if (data.wcag_score !== undefined) setWcagScore(data.wcag_score);
    }).catch(() => {});

    // Subscribe to SSE stream
    const unsubscribe = subscribeScanEvents(
      scanId,
      (event) => {
        setEvents((prev) => [...prev, { ...event, timestamp: new Date().toLocaleTimeString() }]);

        if (event.type === 'phase') {
          setCurrentPhase(event.message || event.phase);
        } else if (event.type === 'crawl_complete') {
          setPagesCrawled(event.pages || 0);
        } else if (event.type === 'observe') {
          if (event.step !== undefined) setActionsTaken(event.step + 1);
        } else if (event.type === 'findings') {
          setFindingsCount(event.total || event.count || 0);
        } else if (event.type === 'a11y_complete') {
          setWcagScore(event.wcag_score);
        } else if (event.type === 'completed') {
          setStatus('completed');
          setCurrentPhase('Scan Completed Successfully');
          if (event.findings) setFindingsCount(event.findings);
          if (event.pages) setPagesCrawled(event.pages);
          getScan(scanId).then(setScanData).catch(() => {});
        } else if (event.type === 'failed') {
          setStatus('failed');
          setCurrentPhase(`Failed: ${event.error || 'Unknown error'}`);
        }
      },
      (err) => {
        console.warn('SSE stream closed or completed:', err);
      }
    );

    return () => unsubscribe();
  }, [scanId]);

  if (!scanId) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 20px', color: 'var(--text-muted)' }}>
        <Activity size={48} color="#334155" style={{ marginBottom: '16px' }} />
        <h3>No Active Scan Dispatched</h3>
        <p style={{ marginTop: '8px' }}>Launch a new scan from the Launchpad to observe real-time agent execution here.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1100px', margin: '30px auto', padding: '0 24px' }}>
      {/* Top Scan Status Bar */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <span className={`badge badge-${status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : 'running'}`}>
              {status === 'running' && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#22d3ee', animation: 'pulseGlow 1.5s infinite' }} />}
              {status}
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>ID: {scanId}</span>
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, wordBreak: 'break-all' }}>
            {targetUrl || scanData?.url || 'Scanning target...'}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={15} /> Current Phase: {currentPhase}
          </p>
        </div>

        {/* Action buttons if completed */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            id="view-findings-action-btn"
            onClick={onViewFindings}
            className="btn btn-primary"
            style={{ padding: '10px 18px', fontSize: '0.88rem' }}
          >
            <ShieldAlert size={16} />
            Inspect {findingsCount} Findings
          </button>

          <a
            href={`/api/scans/${scanId}/report?format=html`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ padding: '10px 18px', fontSize: '0.88rem' }}
          >
            <FileText size={16} />
            HTML Report
          </a>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Pages Crawled</span>
            <Compass size={18} color="#06b6d4" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {pagesCrawled}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>BFS link discovery</span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Agent Actions</span>
            <Zap size={18} color="#8b5cf6" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-purple)' }}>
            {actionsTaken}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Clicks, fills & submits</span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Defects Found</span>
            <ShieldAlert size={18} color="#f43f5e" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f43f5e' }}>
            {findingsCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Console, network & DOM bugs</span>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>WCAG Score</span>
            <Eye size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: wcagScore !== null ? (wcagScore > 80 ? '#34d399' : '#facc15') : 'var(--text-muted)' }}>
            {wcagScore !== null ? `${wcagScore}%` : 'Pending'}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>axe-core 2.1 AA audit</span>
        </div>
      </div>

      {/* Live SSE Event Terminal Feed */}
      <div className="glass-panel" style={{ padding: '20px', borderRadius: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} color="#22d3ee" />
            <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Real-Time Autonomous Agent Event Stream</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {events.length} events received
          </span>
        </div>

        <div style={{
          maxHeight: '400px',
          overflowY: 'auto',
          background: 'rgba(7, 11, 18, 0.95)',
          padding: '16px',
          borderRadius: '10px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.82rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
        }}>
          {events.length === 0 ? (
            <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '30px' }}>
              Awaiting agent events from server...
            </div>
          ) : (
            events.map((evt, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', lineHeight: '1.4' }}>
                <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>[{evt.timestamp}]</span>
                <span style={{
                  color: evt.type === 'findings' ? '#f43f5e' : evt.type === 'plan' ? '#8b5cf6' : evt.type === 'observe' ? '#06b6d4' : evt.type === 'completed' ? '#10b981' : '#94a3b8',
                  fontWeight: 600,
                  flexShrink: 0,
                  textTransform: 'uppercase',
                  fontSize: '0.75rem',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  background: 'rgba(255, 255, 255, 0.05)',
                }}>
                  {evt.type}
                </span>
                <span style={{ color: 'var(--text-primary)', wordBreak: 'break-all' }}>
                  {evt.message || (evt.action ? `Action: ${evt.action} on ${evt.selector || 'page'} — ${evt.reason || ''}` : evt.url ? `URL: ${evt.url}` : JSON.stringify(evt))}
                </span>
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
}
