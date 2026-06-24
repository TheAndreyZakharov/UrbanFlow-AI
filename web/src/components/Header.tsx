export function Header() {
  return (
    <header className="app-header">
      <div className="header-left" />

      <div className="header-brand">
        <img className="header-logo" src="/logo.png" alt="UrbanFlow AI" />
        <div className="header-title-block">
          <strong>UrbanFlow AI</strong>
          <span>OSM-based traffic simulator</span>
        </div>
      </div>

      <div className="header-right">
        <span className="header-status-dot" />
        <span>Backend connected</span>
      </div>
    </header>
  );
}