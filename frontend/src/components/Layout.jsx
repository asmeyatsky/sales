import { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { getApiKey, setApiKey, api } from '../api';

const NAV = [
  {
    to: '/',
    label: 'Dashboard',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z" />
      </svg>
    ),
  },
  {
    to: '/accounts',
    label: 'Accounts',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
  },
  {
    to: '/sequences',
    label: 'Sequences',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    to: '/messages',
    label: 'Messages',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    to: '/decks',
    label: 'Decks',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 3v5a2 2 0 002 2h3" />
      </svg>
    ),
  },
  {
    to: '/crm',
    label: 'CRM',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
  },
];

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/accounts': 'Accounts',
  '/sequences': 'Sequences',
  '/messages': 'Messages',
  '/decks': 'Decks',
  '/crm': 'CRM Sync',
};

export default function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiKey, setApiKeyState] = useState(getApiKey());
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function checkHealth() {
      try {
        await api.get('/health');
        if (!cancelled) setConnected(true);
      } catch {
        if (!cancelled) setConnected(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  function handleApiKeyChange(e) {
    const key = e.target.value;
    setApiKeyState(key);
    setApiKey(key);
  }

  const pageTitle =
    PAGE_TITLES[location.pathname] ||
    location.pathname.slice(1).charAt(0).toUpperCase() +
      location.pathname.slice(2);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 flex flex-col bg-sidebar text-white
          transition-all duration-200 ease-in-out
          ${sidebarOpen ? 'w-60' : 'w-16'}
        `}
        onMouseEnter={() => setSidebarOpen(true)}
        onMouseLeave={() => setSidebarOpen(false)}
      >
        {/* Logo area */}
        <div className="flex items-center h-14 px-4 border-b border-slate-700 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-brand flex items-center justify-center text-white font-bold text-sm shrink-0">
            S
          </div>
          {sidebarOpen && (
            <span className="ml-3 text-sm font-semibold whitespace-nowrap">
              Searce Scout
            </span>
          )}
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-3 space-y-1 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center h-10 px-4 mx-2 rounded-lg transition-colors duration-150 ${
                  isActive
                    ? 'bg-brand text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`
              }
            >
              <span className="shrink-0">{item.icon}</span>
              {sidebarOpen && (
                <span className="ml-3 text-sm font-medium whitespace-nowrap">
                  {item.label}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom branding */}
        <div className="px-4 py-3 border-t border-slate-700 shrink-0">
          {sidebarOpen ? (
            <p className="text-xs text-slate-400">Searce Scout v1.0</p>
          ) : (
            <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs text-slate-400">
              S
            </div>
          )}
        </div>
      </aside>

      {/* Main content area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-200 ${
          sidebarOpen ? 'ml-60' : 'ml-16'
        }`}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-between h-14 px-6 bg-white border-b border-gray-200 shrink-0">
          <h1 className="text-lg font-semibold text-gray-800">{pageTitle}</h1>

          <div className="flex items-center gap-3">
            <input
              type="password"
              placeholder="API Key"
              value={apiKey}
              onChange={handleApiKeyChange}
              className="w-44 px-3 py-1.5 text-xs border border-gray-300 rounded-md bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
            <div className="flex items-center gap-1.5">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  connected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-gray-500">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
