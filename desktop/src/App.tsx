import { FormEvent, useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type AgentStatus = {
  service_state?: string; enrolled?: boolean; endpoint_id?: string; organization_id?: string;
  server_url?: string; agent_version?: string; platform?: string; last_connected_at?: string;
  last_error?: string | null; collector_health?: Record<string, unknown>; pending_batches?: number;
};
type Reply = { ok: boolean; status?: AgentStatus; error?: string };

const formatTime = (value?: string) => value ? new Date(value).toLocaleString() : "Waiting for first connection";

export default function App() {
  const [status, setStatus] = useState<AgentStatus>({ service_state: "starting" });
  const [serverUrl, setServerUrl] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const reply = await invoke<Reply>("agent_request", { request: { command: "status" } });
      if (reply.ok && reply.status) setStatus(reply.status);
      else setMessage(reply.error || "Agent service did not return a status");
    } catch (error) {
      setStatus({ service_state: "unavailable", enrolled: false });
      setMessage(String(error));
    }
  }, []);

  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 15_000); return () => window.clearInterval(timer); }, [refresh]);

  async function enroll(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const reply = await invoke<Reply>("agent_request", { request: { command: "enroll", server_url: serverUrl, token } });
      setToken("");
      if (!reply.ok) throw new Error(reply.error || "Enrollment failed");
      setMessage("Laptop enrolled. Onyx is making its first secure connection."); await refresh();
    } catch (error) { setMessage(String(error)); }
    finally { setBusy(false); }
  }

  async function retry() {
    setBusy(true); setMessage("");
    try { await invoke("agent_request", { request: { command: "retry" } }); setMessage("Connection retry requested."); setTimeout(refresh, 1500); }
    catch (error) { setMessage(String(error)); }
    finally { setBusy(false); }
  }

  async function exportDiagnostics() {
    setBusy(true); setMessage("");
    try { const path = await invoke<string | null>("export_diagnostics"); if (path) setMessage(`Diagnostics saved to ${path}`); }
    catch (error) { setMessage(String(error)); }
    finally { setBusy(false); }
  }

  const connected = Boolean(status.enrolled && status.last_connected_at && !status.last_error);
  return <main>
    <header><div className="brand"><div className="gem">O</div><div><b>ONYX</b><span>Endpoint protection</span></div></div><div className={`pill ${connected ? "good" : "warn"}`}><i />{connected ? "Connected" : status.enrolled ? "Needs attention" : "Setup required"}</div></header>
    <section className="hero">
      <p className="eyebrow">THIS DEVICE</p>
      <h1>{status.enrolled ? "Your laptop is connected to Onyx" : "Connect this laptop to your organization"}</h1>
      <p>{status.enrolled ? "The background service is reporting security health over an encrypted HTTPS connection." : "Use the server address and one-use token supplied by your Onyx administrator."}</p>
    </section>
    {!status.enrolled ? <form className="card enroll" onSubmit={enroll}>
      <label>Onyx server<input type="url" required placeholder="https://api.company.com" value={serverUrl} onChange={e => setServerUrl(e.target.value)} autoComplete="url" /></label>
      <label>One-use enrollment token<input type="password" required placeholder="Paste token" value={token} onChange={e => setToken(e.target.value)} autoComplete="one-time-code" /></label>
      <small>The token is sent directly to your server and discarded immediately.</small>
      <button disabled={busy}>{busy ? "Connecting…" : "Connect laptop"}</button>
    </form> : <>
      <section className="grid">
        <article className="card"><span>LAST SECURE CONNECTION</span><strong>{formatTime(status.last_connected_at)}</strong><small>{status.server_url}</small></article>
        <article className="card"><span>SECURITY COLLECTOR</span><strong>{String(status.collector_health?.state || status.collector_health?.collector || "Checking")}</strong><small>{status.platform} · Agent {status.agent_version || "—"}</small></article>
        <article className="card"><span>QUEUED REPORTS</span><strong>{status.pending_batches ?? 0}</strong><small>Sent automatically when the connection returns</small></article>
      </section>
      {status.last_error && <aside className="error"><b>Connection issue</b><span>{status.last_error}</span></aside>}
      <section className="actions"><button onClick={retry} disabled={busy}>Retry connection</button><button className="secondary" onClick={exportDiagnostics} disabled={busy}>Export diagnostics</button></section>
      <footer>Endpoint ID <code>{status.endpoint_id}</code><br/>Organization <code>{status.organization_id}</code></footer>
    </>}
    {message && <div className="toast" role="status">{message}</div>}
  </main>;
}
