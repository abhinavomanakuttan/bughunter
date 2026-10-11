import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertCircle, Image, Terminal, Wifi, CheckSquare, Search, Filter, ChevronDown, ChevronRight, Eye, Wrench, ListOrdered } from 'lucide-react';
import { getFindings, listScans } from '../api/client';

export default function FindingsList({ selectedScanId, onSelectScan }) {
  const [scans, setScans] = useState([]);
  const [currentScanId, setCurrentScanId] = useState(selectedScanId || '');
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [selectedType, setSelectedType] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);
  const [screenshotModal, setScreenshotModal] = useState(null);

  // Load scans list for dropdown selector
  useEffect(() => {
    listScans(20).then((res) => {
      setScans(res.scans || []);
      if (!currentScanId && res.scans?.length > 0) {
        setCurrentScanId(res.scans[0].id);
      }
    }).catch(() => {});
  }, []);

  // Sync selectedScanId from props
  useEffect(() => {
    if (selectedScanId) {
      setCurrentScanId(selectedScanId);
    }
  }, [selectedScanId]);

  // Load findings whenever currentScanId changes
  useEffect(() => {
    if (!currentScanId) return;
    setLoading(true);
    getFindings(currentScanId).then((res) => {
      setFindings(res.findings || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [currentScanId]);

  // Filters
  const filteredFindings = findings.filter((f) => {
    const matchesSeverity = selectedSeverity === 'ALL' || f.severity === selectedSeverity;
    const matchesType = selectedType === 'ALL' || f.finding_type === selectedType;
    const matchesSearch = !searchQuery || 
      f.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.url?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesType && matchesSearch;
  });

  const getSeverityBadgeClass = (sev) => {
    switch (sev?.toUpperCase()) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-high';
      case 'MEDIUM': return 'badge-medium';
      default: return 'badge-low';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'broken_image': return <Image size={16} color="#fb7185" />;
      case 'console_error': return <Terminal size={16} color="#fb923c" />;
      case 'network_error': return <Wifi size={16} color="#f43f5e" />;
      case 'validation_error': return <AlertCircle size={16} color="#facc15" />;
      case 'accessibility': return <Eye size={16} color="#38bdf8" />;
      default: return <ShieldAlert size={16} color="#94a3b8" />;
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '30px auto', padding: '0 24px' }}>
      {/* Top Header & Scan Selector */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Bug & Defect Explorer</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Investigate discovered vulnerabilities, functional defects, and accessibility violations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Scan:</span>
          <select
            id="scan-selector-dropdown"
            value={currentScanId}
            onChange={(e) => {
              setCurrentScanId(e.target.value);
              if (onSelectScan) onSelectScan(e.target.value);
            }}
            className="input-control"
            style={{ width: 'auto', minWidth: '240px', padding: '8px 12px', fontSize: '0.85rem' }}
          >
            {scans.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id} ({s.status}) — {s.url}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 260px' }}>
          <Search size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '12px' }} />
          <input
            id="findings-search-input"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search findings, selectors, URLs..."
            className="input-control"
            style={{ paddingLeft: '36px', padding: '8px 12px 8px 36px', fontSize: '0.85rem' }}
          />
        </div>

        {/* Severity Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSelectedSeverity(sev)}
              className="btn btn-outline"
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                borderRadius: '6px',
                borderColor: selectedSeverity === sev ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                color: selectedSeverity === sev ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                background: selectedSeverity === sev ? 'rgba(6, 182, 212, 0.1)' : 'transparent',
              }}
            >
              {sev}
            </button>
          ))}
        </div>

        {/* Type Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Type:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="input-control"
            style={{ width: 'auto', padding: '6px 10px', fontSize: '0.8rem' }}
          >
            <option value="ALL">All Categories</option>
            <option value="console_error">Console Error</option>
            <option value="network_error">Network Error</option>
            <option value="broken_image">Broken Image</option>
            <option value="validation_error">Validation Error</option>
            <option value="accessibility">Accessibility</option>
          </select>
        </div>
      </div>

      {/* Findings List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          Loading defect findings...
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
          <ShieldAlert size={40} color="#334155" style={{ marginBottom: '12px' }} />
          <h4>No defects found matching criteria</h4>
          <p style={{ fontSize: '0.85rem', marginTop: '6px' }}>Try relaxing your search filter or select another scan run.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
            Showing {filteredFindings.length} of {findings.length} total findings
          </div>

          {filteredFindings.map((finding) => {
            const isExpanded = expandedId === finding.id;
            return (
              <div
                key={finding.id}
                className="glass-panel"
                style={{
                  padding: '18px 22px',
                  transition: 'all 0.2s ease',
                  border: isExpanded ? '1px solid var(--border-glow)' : '1px solid var(--border-subtle)',
                }}
              >
                {/* Header Row */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : finding.id)}
                  style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', cursor: 'pointer', gap: '16px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                    <div style={{ marginTop: '2px' }}>
                      {getTypeIcon(finding.finding_type)}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                        <span className={`badge ${getSeverityBadgeClass(finding.severity)}`}>
                          {finding.severity}
                        </span>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                          {finding.finding_type?.replace('_', ' ')}
                        </span>
                      </div>
                      <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {finding.title}
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {finding.url}
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {finding.screenshot_path && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setScreenshotModal(`/api/screenshots/${finding.scan_id}/${finding.screenshot_path.split(/[\\/]/).pop()}`);
                        }}
                        className="btn btn-outline"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Image size={14} /> View Screenshot
                      </button>
                    )}
                    {isExpanded ? <ChevronDown size={18} color="#94a3b8" /> : <ChevronRight size={18} color="#94a3b8" />}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ marginTop: '18px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {finding.description && (
                      <div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>Description</span>
                        <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                          {finding.description}
                        </p>
                      </div>
                    )}

                    {finding.selector && (
                      <div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>Target Selector</span>
                        <pre style={{ marginTop: '4px', padding: '8px 12px', background: 'rgba(7, 11, 18, 0.8)', borderRadius: '6px', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                          {finding.selector}
                        </pre>
                      </div>
                    )}

                    {finding.reproduction_steps && finding.reproduction_steps.length > 0 && (
                      <div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <ListOrdered size={14} /> Steps to Reproduce
                        </span>
                        <ol style={{ marginTop: '6px', paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {finding.reproduction_steps.map((st, i) => (
                            <li key={i} style={{ marginBottom: '4px' }}>{st}</li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {finding.recommended_fix && (
                      <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Wrench size={14} /> Recommended Remediation
                        </span>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                          {finding.recommended_fix}
                        </p>
                      </div>
                    )}

                    {finding.evidence && Object.keys(finding.evidence).length > 0 && (
                      <div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>Technical Evidence</span>
                        <pre style={{ marginTop: '4px', padding: '10px', background: 'rgba(7, 11, 18, 0.8)', borderRadius: '6px', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: '#94a3b8', maxHeight: '180px', overflowY: 'auto' }}>
                          {JSON.stringify(finding.evidence, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Screenshot Modal */}
      {screenshotModal && (
        <div
          onClick={() => setScreenshotModal(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px',
          }}
        >
          <div style={{ maxWidth: '90vw', maxHeight: '90vh', position: 'relative' }}>
            <img
              src={screenshotModal}
              alt="Bug Screenshot"
              style={{ maxWidth: '100%', maxHeight: '85vh', borderRadius: '12px', border: '1px solid var(--border-subtle)', boxShadow: '0 20px 50px rgba(0,0,0,0.8)' }}
            />
            <div style={{ textAlign: 'center', marginTop: '12px' }}>
              <button onClick={() => setScreenshotModal(null)} className="btn btn-secondary">
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
