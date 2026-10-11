import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Launchpad from './components/Launchpad';
import LiveScanMonitor from './components/LiveScanMonitor';
import FindingsList from './components/FindingsList';
import ScanHistory from './components/ScanHistory';
import { fetchHealth } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('launchpad');
  const [health, setHealth] = useState(null);
  const [currentScanId, setCurrentScanId] = useState(null);
  const [targetUrl, setTargetUrl] = useState('');

  // Poll server health on mount
  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => console.warn('Backend offline or not reachable:', err));

    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(() => setHealth(null));
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  const handleScanStarted = (scanId, url) => {
    setCurrentScanId(scanId);
    setTargetUrl(url);
    setActiveTab('monitor');
  };

  const handleSelectScanForFindings = (scanId) => {
    setCurrentScanId(scanId);
    setActiveTab('findings');
  };

  const handleMonitorScan = (scanId) => {
    setCurrentScanId(scanId);
    setActiveTab('monitor');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        currentScanId={currentScanId}
      />

      <main style={{ flex: 1, paddingBottom: '60px' }}>
        {activeTab === 'launchpad' && (
          <Launchpad onScanStarted={handleScanStarted} />
        )}

        {activeTab === 'monitor' && (
          <LiveScanMonitor
            scanId={currentScanId}
            targetUrl={targetUrl}
            onViewFindings={() => setActiveTab('findings')}
          />
        )}

        {activeTab === 'findings' && (
          <FindingsList
            selectedScanId={currentScanId}
            onSelectScan={setCurrentScanId}
          />
        )}

        {activeTab === 'history' && (
          <ScanHistory
            onSelectScan={handleSelectScanForFindings}
            onMonitorScan={handleMonitorScan}
          />
        )}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '20px 32px',
        textAlign: 'center',
        fontSize: '0.82rem',
        color: 'var(--text-muted)',
        background: 'rgba(7, 11, 18, 0.8)',
      }}>
        BugHunter — Autonomous AI Software Testing Agent Platform · Built with FastAPI, Playwright & React
      </footer>
    </div>
  );
}
