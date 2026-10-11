import React, { useState, useEffect } from 'react';
import { History, FileText, ExternalLink, ArrowRight, Activity, ShieldAlert, RefreshCw, Eye } from 'lucide-react';
import { listScans } from '../api/client';

export default function ScanHistory({ onSelectScan, onMonitorScan }) {
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadScans = () => {
    setLoading(true);
    listScans(50).then((res) => {
      setScans(res.scans || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    loadScans();
  }, []);

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'badge-completed';
      case 'running': return 'badge-running';
      default: return 'badge-failed';
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '30px auto', padding: '0 24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Scan Execution History</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            All past autonomous scans, page crawl depth, findings count, and generated reports.
          </p>
        </div>

        <button onClick={loadScans} className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
          <RefreshCw size={15} /> Refresh List
        </button>
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ overflowX: 'auto', borderRadius: '16px' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading scan history...
          </div>
        ) : scans.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <History size={40} color="#334155" style={{ marginBottom: '12px' }} />
            <h4>No scans recorded yet</h4>
            <p style={{ fontSize: '0.85rem', marginTop: '6px' }}>Dispatch your first scan from the Launchpad!</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(15, 23, 42, 0.6)', color: 'var(--text-muted)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '16px 20px' }}>Target URL & ID</th>
                <th style={{ padding: '16px 16px' }}>Status</th>
                <th style={{ padding: '16px 16px' }}>Pages</th>
                <th style={{ padding: '16px 16px' }}>Findings</th>
                <th style={{ padding: '16px 16px' }}>WCAG</th>
                <th style={{ padding: '16px 16px' }}>Started At</th>
                <th style={{ padding: '16px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((s) => (
                <tr
                  key={s.id}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ fontWeight: 700, color: 'var(--text-primary)', wordBreak: 'break-all' }}>
                      {s.url}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {s.id}
                    </div>
                  </td>

                  <td style={{ padding: '16px 16px' }}>
                    <span className={`badge ${getStatusBadge(s.status)}`}>
                      {s.status}
                    </span>
                  </td>

                  <td style={{ padding: '16px 16px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {s.pages_crawled || 0}
                  </td>

                  <td style={{ padding: '16px 16px' }}>
                    <span style={{ fontWeight: 700, color: s.findings_count > 0 ? '#f43f5e' : 'var(--text-muted)' }}>
                      {s.findings_count || 0}
                    </span>
                  </td>

                  <td style={{ padding: '16px 16px', fontWeight: 600, color: s.wcag_score > 80 ? '#34d399' : '#facc15' }}>
                    {s.wcag_score !== undefined ? `${s.wcag_score}%` : '—'}
                  </td>

                  <td style={{ padding: '16px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                  </td>

                  <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '8px' }}>
                      <button
                        onClick={() => onSelectScan(s.id)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                        title="View Bug Findings"
                      >
                        <ShieldAlert size={14} /> Defects
                      </button>

                      {s.report_html_path && (
                        <a
                          href={`/api/scans/${s.id}/report?format=html`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-outline"
                          style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                          title="Open HTML Report"
                        >
                          <FileText size={14} /> HTML
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
