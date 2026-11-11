
import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [emailText, setEmailText] = useState("");
  const [proposal, setProposal] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  const [form, setForm] = useState({
    client: "",
    email: "",
    project: "",
    description: "",
    status: "Pending",
  });

  async function loadRequests() {
    try {
      setLoading(true);
      const response = await fetch(`${API}/api/requests`);
      if (!response.ok) throw new Error("Could not load requests");
      const data = await response.json();
      setRequests(data.requests || []);
      setMessage("");
    } catch (error) {
      setMessage("Backend connection failed. Please start the backend server.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  function handleChange(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function saveRequest(event) {
    event.preventDefault();

    try {
      const url = selectedId
        ? `${API}/api/requests/${selectedId}`
        : `${API}/api/requests`;

      const response = await fetch(url, {
        method: selectedId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Save failed");

      setMessage(selectedId ? "Request updated successfully!" : "Request added successfully!");
      resetForm();
      loadRequests();
    } catch (error) {
      setMessage(error.message);
    }
  }

  function editRequest(item) {
    setSelectedId(item.id);
    setForm({
      client: item.client || "",
      email: item.email || "",
      project: item.project || "",
      description: item.description || "",
      status: item.status || "Pending",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() {
    setSelectedId(null);
    setForm({
      client: "",
      email: "",
      project: "",
      description: "",
      status: "Pending",
    });
  }

  async function deleteRequest(id) {
    if (!window.confirm("Are you sure you want to delete this request?")) return;

    try {
      const response = await fetch(`${API}/api/requests/${id}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Delete failed");
      setMessage("Request deleted successfully!");
      loadRequests();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function extractEmail() {
    try {
      setLoading(true);
      const response = await fetch(`${API}/api/extract-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: emailText }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Extraction failed");

      const extracted = data.extracted_data;
      setForm({
        client: extracted.client || "",
        email: extracted.email || "",
        project: extracted.project || "",
        description: extracted.description || "",
        status: "Pending",
      });
      setSelectedId(null);
      setMessage("Email information extracted. Review the details and save the request.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function generateProposal(id) {
    try {
      setLoading(true);
      setSelectedId(id);

      const response = await fetch(`${API}/api/generate-proposal/${id}`, {
        method: "POST",
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Proposal generation failed");

      setProposal(data.proposal);
      setMessage("Proposal generated successfully!");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadPDF() {
    if (!proposal || !selectedId) return;

    try {
      const response = await fetch(
        `${API}/api/generate-proposal-pdf/${selectedId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(proposal),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "PDF download failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `proposal_${selectedId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      setMessage("PDF downloaded successfully!");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function sendProposal() {
    if (!proposal || !selectedId) return;

    const recipient = requests.find((item) => item.id === selectedId)?.email;
    if (!window.confirm(`Send this proposal to ${recipient}?`)) return;

    try {
      setLoading(true);
      const response = await fetch(`${API}/api/send-proposal/${selectedId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(proposal),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Email sending failed");

      setMessage(data.message || "Proposal email sent successfully!");
      await loadRequests();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>ProposalAI</h1>
          <p>AI-Powered Email-to-Proposal Generation System</p>
        </div>
        <button onClick={loadRequests}>Refresh Requests</button>
      </header>

      {message && <div className="message">{message}</div>}

      <section className="stats">
        <div className="stat-card">
          <h3>Total Requests</h3>
          <strong>{requests.length}</strong>
        </div>
        <div className="stat-card">
          <h3>Pending</h3>
          <strong>{requests.filter((r) => r.status === "Pending").length}</strong>
        </div>
        <div className="stat-card">
          <h3>Sent</h3>
          <strong>{requests.filter((r) => r.status === "Sent").length}</strong>
        </div>
      </section>

      <section className="panel">
        <h2>AI Email Extraction</h2>
        <p>Paste a client email to extract project information.</p>
        <textarea
          rows="5"
          value={emailText}
          onChange={(e) => setEmailText(e.target.value)}
          placeholder="Paste the client email here..."
        />
        <button onClick={extractEmail} disabled={loading || !emailText.trim()}>
          Extract Email Information
        </button>
      </section>

      <section className="panel">
        <h2>{selectedId ? "Edit Client Request" : "Add Client Request"}</h2>
        <form onSubmit={saveRequest}>
          <div className="form-grid">
            <input name="client" value={form.client} onChange={handleChange} placeholder="Client name" required />
            <input name="email" type="email" value={form.email} onChange={handleChange} placeholder="Client email" required />
            <input name="project" value={form.project} onChange={handleChange} placeholder="Project name" required />
            <select name="status" value={form.status} onChange={handleChange}>
              <option>Pending</option>
              <option>Under Review</option>
              <option>Approved</option>
              <option>Sent</option>
            </select>
          </div>
          <textarea
            name="description"
            rows="3"
            value={form.description}
            onChange={handleChange}
            placeholder="Project description"
          />
          <div className="actions">
            <button type="submit">{selectedId ? "Update Request" : "Add Request"}</button>
            <button type="button" className="secondary" onClick={resetForm}>Clear</button>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Client Requests</h2>
        {loading && <p>Loading...</p>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Client</th>
                <th>Email</th>
                <th>Project</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.client}</td>
                  <td>{item.email}</td>
                  <td>{item.project}</td>
                  <td><span className="status">{item.status}</span></td>
                  <td>
                    <div className="table-actions">
                      <button onClick={() => generateProposal(item.id)}>Generate</button>
                      <button className="secondary" onClick={() => editRequest(item)}>Edit</button>
                      <button className="danger" onClick={() => deleteRequest(item.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && requests.length === 0 && (
                <tr><td colSpan="6">No requests found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {proposal && (
        <section className="panel proposal">
          <h2>{proposal.title}</h2>
          <p><strong>Client:</strong> {proposal.client}</p>
          <h3>Executive Summary</h3>
          <p>{proposal.executive_summary}</p>

          {["project_objectives", "scope_of_work", "deliverables", "assumptions", "next_steps"].map((field) => (
            <div key={field}>
              <h3>{field.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</h3>
              <ul>
                {(proposal[field] || []).map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          ))}

          <h3>Timeline</h3>
          <p>{typeof proposal.timeline === "object" ? JSON.stringify(proposal.timeline) : proposal.timeline}</p>
          <h3>Pricing</h3>
          <p>{typeof proposal.pricing === "object" ? JSON.stringify(proposal.pricing) : proposal.pricing}</p>

          <div className="actions">
            <button onClick={downloadPDF}>Download PDF</button>
            <button onClick={sendProposal}>Send Proposal Email</button>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
