// frontend/src/App.tsx
/** Main application component. */
import { HealthStatus } from "./components/HealthStatus";
import "./App.css";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Beacon Observatory</h1>
          <p className="subtitle">AI/ML developer tools for pstack agent workflows</p>
        </div>
        <div className="header-meta">
          <span className="version">v1.0.0</span>
          <span className="author">Alan Vo &middot; AI & Machine Learning</span>
        </div>
      </header>

      <main className="app-main">
        <section className="health-section" aria-labelledby="health-heading">
          <h2 id="health-heading">System Health</h2>
          <HealthStatus detailed={true} />
        </section>

        <section className="features-section" aria-labelledby="features-heading">
          <h2 id="features-heading">Capabilities</h2>
          <div className="features-grid">
            <article className="feature-card">
              <h3>Skill Registry</h3>
              <p>Manage pstack skills, playbooks, and principles with full CRUD API and persistent storage.</p>
              <span className="status planned">Planned</span>
            </article>
            <article className="feature-card">
              <h3>Multi-Agent Config Generator</h3>
              <p>Generate agent-specific configurations for Claude, Codex, Copilot, Pi, OpenCode, Gemini, and Prime Agent.</p>
              <span className="status planned">Planned</span>
            </article>
            <article className="feature-card">
              <h3>Hook Effectiveness Analyzer</h3>
              <p>Analyze session logs to measure hook reach and follow-through rates across agent types (Issue #264).</p>
              <span className="status planned">Planned</span>
            </article>
            <article className="feature-card">
              <h3>OIDC Authentication</h3>
              <p>Secure authentication with Keycloak, roles (viewer/operator/admin), and local demo mode.</p>
              <span className="status planned">Planned</span>
            </article>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>Beacon Observatory &copy; 2026 Alan Vo {"<alanvo@gmail.com>"} — MIT License</p>
      </footer>
    </div>
  );
}

export default App;