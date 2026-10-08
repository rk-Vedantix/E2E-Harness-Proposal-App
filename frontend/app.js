const API = "/api";
let META = null;
let PROJECTS = [];
let CURRENT = null; // full project detail incl. contributions + proposals
let ACTIVE_TAB = "form";
let VIEW_VERSION = null;

async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`${res.status}: ${t}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

async function loadMeta() {
  META = await api("/meta");
}

async function loadProjects() {
  PROJECTS = await api("/projects");
  renderProjectList();
}

function renderProjectList() {
  const el = document.getElementById("project-list");
  if (!PROJECTS.length) {
    el.innerHTML = `<div class="small">No projects yet.</div>`;
    return;
  }
  el.innerHTML = PROJECTS.map(p => `
    <div class="project-item ${CURRENT && CURRENT.id === p.id ? "active" : ""}" onclick="selectProject(${p.id})">
      ${escapeHtml(p.name)}
      <span class="cust">${escapeHtml(p.customer || "no customer set")}</span>
    </div>
  `).join("");
}

async function createProject() {
  const name = document.getElementById("new-project-name").value.trim();
  const customer = document.getElementById("new-project-customer").value.trim();
  if (!name) { alert("Give the project a name."); return; }
  const fd = new FormData();
  fd.append("name", name);
  fd.append("customer", customer);
  const p = await api("/projects", { method: "POST", body: fd });
  document.getElementById("new-project-name").value = "";
  document.getElementById("new-project-customer").value = "";
  await loadProjects();
  selectProject(p.id);
}

async function selectProject(id) {
  CURRENT = await api(`/projects/${id}`);
  VIEW_VERSION = CURRENT.proposals.length ? CURRENT.proposals[0].version : null;
  renderProjectList();
  renderMain();
}

function renderMain() {
  const main = document.getElementById("main");
  if (!CURRENT) { main.innerHTML = `<div class="empty">Select or create a project to begin.</div>`; return; }

  main.innerHTML = `
    <div class="card">
      <div class="flex-between">
        <div>
          <h2 style="margin-bottom:2px;">${escapeHtml(CURRENT.name)}</h2>
          <div class="small">${escapeHtml(CURRENT.customer || "No customer set")} · ${CURRENT.contributions.length} contribution(s) on file</div>
        </div>
        <button onclick="generateProposal()">Generate draft proposal</button>
      </div>
    </div>

    <div class="card">
      <h2>Add an input</h2>
      <div class="small" style="margin-bottom:10px;">
        Multiple people can contribute to the same project — the business-development manager who met the customer,
        and the engineers / project managers who will actually scope the work. Each contribution is tagged by
        who added it so the draft (and any reviewer) can see where information came from.
      </div>
      <label>Your name</label>
      <input id="c-name" placeholder="e.g. Priya Shah">
      <div class="flex">
        <div style="flex:1;">
          <label>Your role</label>
          <input id="c-role" placeholder="e.g. Business Development Manager">
        </div>
        <div style="flex:1;">
          <label>Discipline (optional)</label>
          <select id="c-discipline">
            <option value="">— not specified —</option>
            ${META.discipline_full.map((d, i) => `<option value="${META.disciplines[i]}">${d}</option>`).join("")}
          </select>
        </div>
      </div>

      <div class="tabs">
        <button class="tab-btn ${ACTIVE_TAB === "form" ? "active" : ""}" onclick="setTab('form')">Structured form</button>
        <button class="tab-btn ${ACTIVE_TAB === "upload" ? "active" : ""}" onclick="setTab('upload')">Document upload</button>
        <button class="tab-btn ${ACTIVE_TAB === "paste" ? "active" : ""}" onclick="setTab('paste')">Paste email / text</button>
        <button class="tab-btn ${ACTIVE_TAB === "notes" ? "active" : ""}" onclick="setTab('notes')">Meeting / verbal notes</button>
      </div>

      <div class="tab-content ${ACTIVE_TAB === "form" ? "active" : ""}" id="tab-form">
        <div class="flex">
          <div style="flex:1;">
            <label>Project type (if known)</label>
            <select id="f-project-type">
              <option value="">— not sure yet —</option>
              ${META.domains.map(d => `<option value="${d.label}">${d.label}</option>`).join("")}
            </select>
          </div>
          <div style="flex:1;">
            <label>Annual volume</label>
            <input id="f-volume" placeholder="e.g. 18,000 units per year">
          </div>
        </div>
        <label>Target regions / markets</label>
        <input id="f-regions" placeholder="e.g. UK, EU, India">
        <label>Key requirements / notes</label>
        <textarea id="f-notes" rows="4" placeholder="Anything the customer specified: voltage, standards, environment, timing..."></textarea>
        <button onclick="submitContribution('form')">Add form input</button>
      </div>

      <div class="tab-content ${ACTIVE_TAB === "upload" ? "active" : ""}" id="tab-upload">
        <label>Reference document (.pdf, .docx, .txt)</label>
        <input type="file" id="u-file">
        <label>Any covering note (optional)</label>
        <textarea id="u-note" rows="2" placeholder="e.g. Customer RFQ attached, see section 3 for environmental requirements"></textarea>
        <button onclick="submitContribution('upload')">Add document</button>
      </div>

      <div class="tab-content ${ACTIVE_TAB === "paste" ? "active" : ""}" id="tab-paste">
        <label>Paste an email thread or free text</label>
        <textarea id="p-text" rows="6" placeholder="Paste the customer email or spec text here..."></textarea>
        <button onclick="submitContribution('paste')">Add pasted text</button>
      </div>

      <div class="tab-content ${ACTIVE_TAB === "notes" ? "active" : ""}" id="tab-notes">
        <label>Meeting / verbal notes</label>
        <div class="small" style="margin-bottom:8px;">
          For the person who met the customer (e.g. sales / BD) to write up what was discussed, before an engineer
          gets involved. (A future version would accept an audio recording and transcribe it automatically —
          this prototype takes typed notes instead.)
        </div>
        <textarea id="n-text" rows="6" placeholder="e.g. Customer wants a harness for their new electric van, roughly 5000/year, needs to survive wash-down..."></textarea>
        <button onclick="submitContribution('notes')">Add notes</button>
      </div>
    </div>

    <div class="card">
      <h2>Contributions on file (${CURRENT.contributions.length})</h2>
      ${renderContributions()}
    </div>

    <div class="card">
      <div class="flex-between">
        <h2 style="margin:0;">Draft proposal</h2>
        ${renderVersionPicker()}
      </div>
      ${renderProposal()}
    </div>
  `;
}

function renderVersionPicker() {
  if (!CURRENT.proposals.length) return "";
  return `
    <select style="width:auto;margin:0;" onchange="VIEW_VERSION=parseInt(this.value);renderMain();">
      ${CURRENT.proposals.map(p => `<option value="${p.version}" ${p.version === VIEW_VERSION ? "selected" : ""}>Version ${p.version}</option>`).join("")}
    </select>
  `;
}

function renderContributions() {
  if (!CURRENT.contributions.length) {
    return `<div class="small">Nothing added yet. Use the panel above — any single input type is enough to generate a first draft, but a draft improves as more contributors add their view.</div>`;
  }
  return `<div class="contrib-list">` + CURRENT.contributions.map(c => `
    <div class="contrib-item">
      <div class="meta">
        <strong>${escapeHtml(c.contributor_name || "Unnamed")}</strong>
        ${c.contributor_role ? " · " + escapeHtml(c.contributor_role) : ""}
        ${c.discipline ? ` · <span class="badge">${c.discipline}</span>` : ""}
        · ${c.input_type}${c.source_name ? " · " + escapeHtml(c.source_name) : ""}
        · ${new Date(c.created_at + "Z").toLocaleString()}
      </div>
      <div class="content">${escapeHtml((c.content || "").slice(0, 220))}${(c.content || "").length > 220 ? "…" : ""}</div>
    </div>
  `).join("") + `</div>`;
}

function renderProposal() {
  const proposal = CURRENT.proposals.find(p => p.version === VIEW_VERSION);
  if (!proposal) {
    return `<div class="empty">No draft generated yet. Add at least one contribution above, then click "Generate draft proposal".</div>`;
  }
  const c = proposal.content;
  const disc = META.disciplines;

  const domainBadges = c.matched_domains.map(d => `<span class="badge">${escapeHtml(d.label)}</span>`).join("");
  const addonNotes = (c.addon_notes || []).map(n => `<li>${escapeHtml(n)}</li>`).join("");

  const wpRows = c.work_packages.map(wp => `
    <tr>
      <td>${wp[0]}</td>
      <td>${escapeHtml(wp[1])}<div class="small">${escapeHtml(wp[2])}</div></td>
      ${wp[3].map(h => `<td style="text-align:center;">${h}</td>`).join("")}
      <td style="text-align:center;"><strong>${wp[3].reduce((a, b) => a + b, 0)}</strong></td>
    </tr>
  `).join("");

  const totalRow = `
    <tr class="total-row">
      <td></td><td>Base total</td>
      ${c.discipline_totals.map(h => `<td style="text-align:center;">${h}</td>`).join("")}
      <td style="text-align:center;">${c.base_hours}</td>
    </tr>
    <tr class="total-row">
      <td></td><td>Risk contingency (${c.contingency_pct}%)</td>
      ${disc.map(() => "<td></td>").join("")}
      <td style="text-align:center;">${c.contingency_hours}</td>
    </tr>
    <tr class="total-row">
      <td></td><td>Total with contingency</td>
      ${disc.map(() => "<td></td>").join("")}
      <td style="text-align:center;"><strong>${c.total_hours}</strong></td>
    </tr>
  `;

  const standardsRows = c.standards.map(s => `<tr><td>${escapeHtml(s[0])}</td><td>${escapeHtml(s[1])}</td></tr>`).join("");
  const risksRows = c.risks.map(r => `<tr><td>${escapeHtml(r[0])}</td><td>${escapeHtml(r[1])}</td><td>${escapeHtml(r[2])}</td></tr>`).join("");

  return `
    <div class="version-pill">v${proposal.version}</div>
    <span class="small">generated ${new Date(proposal.created_at + "Z").toLocaleString()} from ${c.contribution_count} contribution(s)</span>
    <div style="margin:10px 0;">${domainBadges} ${c.hybrid ? '<span class="badge warn">hybrid scope — check for overlap</span>' : ""}</div>
    ${c.volume_note ? `<div class="small">Volume detected in inputs: <strong>${escapeHtml(c.volume_note)}</strong></div>` : ""}
    ${addonNotes ? `<ul class="clean">${addonNotes}</ul>` : ""}

    <h3>Applicable standards (draft)</h3>
    <table><tr><th>Standard</th><th>Why it applies</th></tr>${standardsRows}</table>

    <h3>Work packages and effort (hours)</h3>
    <div style="overflow-x:auto;">
    <table>
      <tr><th>ID</th><th>Work package</th>${disc.map(d => `<th>${d}</th>`).join("")}<th>Total</th></tr>
      ${wpRows}
      ${totalRow}
    </table>
    </div>

    <h3>Assumptions</h3>
    <ul class="clean">${c.assumptions.map(a => `<li>${escapeHtml(a)}</li>`).join("")}</ul>

    <h3>Exclusions</h3>
    <ul class="clean">${c.exclusions.map(a => `<li>${escapeHtml(a)}</li>`).join("")}</ul>

    <h3>Risks</h3>
    <table><tr><th>Risk</th><th>Impact</th><th>Mitigation</th></tr>${risksRows}</table>

    <h3>Open clarification questions ${c.clarifications.length ? `<span class="badge warn">${c.clarifications.length} open</span>` : ""}</h3>
    ${c.clarifications.length ? `<ul class="clean">${c.clarifications.map(q => `<li>${escapeHtml(q)}</li>`).join("")}</ul>` : `<div class="small">None auto-detected from the current inputs.</div>`}

    <h3>Contributors reflected in this draft</h3>
    <table><tr><th>Name</th><th>Role</th><th>Discipline</th><th>Input type</th></tr>
    ${c.contributors.map(ct => `<tr><td>${escapeHtml(ct.name)}</td><td>${escapeHtml(ct.role)}</td><td>${escapeHtml(ct.discipline)}</td><td>${ct.input_type}</td></tr>`).join("")}
    </table>

    <div class="flex" style="margin-top:14px;">
      <a href="${API}/projects/${CURRENT.id}/proposals/${proposal.version}/download"><button class="secondary">Download as Word (.docx)</button></a>
    </div>
    <div class="small" style="margin-top:8px;">Approval status: DRAFT. Requires technical review, commercial review and management approval before issue.</div>
  `;
}

function setTab(t) { ACTIVE_TAB = t; renderMain(); }

async function submitContribution(kind) {
  const name = document.getElementById("c-name").value.trim();
  const role = document.getElementById("c-role").value.trim();
  const discipline = document.getElementById("c-discipline").value;
  if (!name) { alert("Enter your name so this contribution is attributed."); return; }

  const fd = new FormData();
  fd.append("contributor_name", name);
  fd.append("contributor_role", role);
  fd.append("discipline", discipline);

  if (kind === "form") {
    fd.append("input_type", "form");
    fd.append("text_content", document.getElementById("f-notes").value);
    fd.append("structured_fields", JSON.stringify({
      project_type: document.getElementById("f-project-type").value,
      annual_volume: document.getElementById("f-volume").value,
      target_regions: document.getElementById("f-regions").value,
    }));
  } else if (kind === "upload") {
    const file = document.getElementById("u-file").files[0];
    if (!file) { alert("Choose a file first."); return; }
    fd.append("input_type", "upload");
    fd.append("text_content", document.getElementById("u-note").value);
    fd.append("file", file);
  } else if (kind === "paste") {
    fd.append("input_type", "paste");
    fd.append("text_content", document.getElementById("p-text").value);
  } else if (kind === "notes") {
    fd.append("input_type", "notes");
    fd.append("text_content", document.getElementById("n-text").value);
  }

  await api(`/projects/${CURRENT.id}/contributions`, { method: "POST", body: fd });
  CURRENT = await api(`/projects/${CURRENT.id}`);
  renderMain();
}

async function generateProposal() {
  if (!CURRENT.contributions.length) { alert("Add at least one input before generating a draft."); return; }
  const res = await api(`/projects/${CURRENT.id}/generate`, { method: "POST" });
  CURRENT = await api(`/projects/${CURRENT.id}`);
  VIEW_VERSION = res.version;
  renderMain();
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

(async function init() {
  await loadMeta();
  await loadProjects();
  renderMain();
})();
