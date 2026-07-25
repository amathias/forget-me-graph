(() => {
  "use strict";

  const state = {
    overview: null,
    plan: null,
    selectorValue: null,
    running: false,
  };

  const byId = (id) => document.getElementById(id);
  const text = (value) => document.createTextNode(String(value));

  function setText(element, value) {
    element.replaceChildren(text(value));
  }

  function shortHash(value, visible = 12) {
    if (!value || value.length <= visible * 2) return value || "—";
    return `${value.slice(0, visible)}…${value.slice(-visible)}`;
  }

  function maskedToken(value) {
    if (!value) return "subj_••••••••••••••••";
    const suffix = value.slice(-6);
    return `subj_••••••••••${suffix}`;
  }

  function showToast(message, kind = "info") {
    const toast = byId("toast");
    toast.classList.toggle("error", kind === "error");
    setText(toast, message);
    toast.classList.add("visible");
    window.setTimeout(() => toast.classList.remove("visible"), 4800);
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(
        typeof payload.detail === "string" ? payload.detail : "The request failed closed.",
      );
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function gateMarkup(title, detail, value, ready) {
    const gate = document.createElement("div");
    gate.className = "gate";
    gate.dataset.state = ready ? "ready" : "blocked";
    const icon = document.createElement("span");
    icon.className = "gate-icon";
    setText(icon, ready ? "OK" : "×");
    const copy = document.createElement("div");
    const heading = document.createElement("strong");
    setText(heading, title);
    const small = document.createElement("small");
    setText(small, `${detail}: ${value}`);
    copy.append(heading, small);
    gate.append(icon, copy);
    return gate;
  }

  async function refreshReadiness() {
    const header = byId("header-status");
    header.dataset.state = "checking";
    header.lastElementChild.textContent = "Checking live gates";
    byId("refresh-readiness").disabled = true;
    try {
      const response = await fetch("/api/readiness");
      const payload = await response.json();
      const checks = payload.checks || {};
      const fixtureReady = checks.fixture === "ready";
      const catalogReady = checks.datahub_catalog === "ready";
      const capabilities = Array.isArray(checks.datahub_capabilities)
        ? checks.datahub_capabilities
        : [];
      const mcpReady =
        checks.datahub_mcp === "connected" &&
        capabilities.includes("get_entities") &&
        capabilities.includes("get_lineage");
      byId("gate-list").replaceChildren(
        gateMarkup("Fixture marker", "synthetic estate", checks.fixture || "unknown", fixtureReady),
        gateMarkup(
          "Exact DataHub catalog",
          "10 assets / 9 edges",
          checks.datahub_catalog || "unknown",
          catalogReady,
        ),
        gateMarkup(
          "MCP capabilities",
          "entity + lineage",
          capabilities.length ? capabilities.join(", ") : checks.datahub_mcp || "unknown",
          mcpReady,
        ),
      );
      header.dataset.state = payload.ready ? "ready" : "blocked";
      header.lastElementChild.textContent = payload.ready
        ? "Live gates ready"
        : "Execution blocked";
      setText(
        byId("readiness-code"),
        payload.ready
          ? "200 · exact catalog verified"
          : `${response.status} · fail-closed readiness`,
      );
    } catch (_error) {
      header.dataset.state = "blocked";
      header.lastElementChild.textContent = "Readiness unavailable";
      byId("gate-list").replaceChildren(
        gateMarkup("Readiness endpoint", "non-mutating probe", "unavailable", false),
      );
      setText(byId("readiness-code"), "Connection failed closed");
    } finally {
      byId("refresh-readiness").disabled = false;
    }
  }

  function graphStage(node) {
    if (node.artifact_type === "ml_model") return "Serve";
    if (node.artifact_type === "training_snapshot") return "Train";
    if (node.artifact_type === "feature_table") return "Feature";
    if (node.name.toLowerCase().includes("raw")) return "Ingest";
    return "Materialize";
  }

  function nodeTone(node) {
    if (node.policy === "exempt") return "exempt";
    if (["ml_model", "training_snapshot", "feature_table"].includes(node.artifact_type)) {
      return "learned";
    }
    if (node.name.toLowerCase().includes("raw")) return "source";
    return "derived";
  }

  function renderGraph(overview) {
    const stages = ["Ingest", "Materialize", "Feature", "Train", "Serve"];
    const grouped = new Map(stages.map((stage) => [stage, []]));
    overview.nodes.forEach((node) => grouped.get(graphStage(node)).push(node));
    const grid = byId("graph-grid");
    const columns = stages.map((stage) => {
      const column = document.createElement("section");
      column.className = "graph-column";
      const heading = document.createElement("h3");
      heading.className = "graph-column-title";
      setText(heading, stage);
      column.append(heading);
      grouped.get(stage).forEach((node) => {
        const card = document.createElement("article");
        card.className = `node-card ${nodeTone(node)}`;
        const name = document.createElement("strong");
        setText(name, node.name);
        const meta = document.createElement("small");
        setText(meta, `${node.platform} · ${node.artifact_type.replaceAll("_", " ")}`);
        const policy = document.createElement("span");
        setText(policy, node.policy === "exempt" ? "EXEMPT" : node.adapter);
        card.append(name, meta, policy);
        column.append(card);
      });
      return column;
    });
    grid.replaceChildren(...columns);
    setText(
      byId("graph-count"),
      `${overview.nodes.length} exact assets · ${overview.edges.length} lineage edges`,
    );
  }

  function proofValue(container, label, value) {
    const row = document.createElement("div");
    const name = document.createElement("span");
    setText(name, label);
    const code = document.createElement("code");
    code.title = value || "Not available in this source checkout";
    setText(code, value ? shortHash(value) : "Not bundled");
    row.append(name, code);
    container.append(row);
  }

  function renderCoordinatorProof(evidence) {
    const container = byId("coordinator-proof");
    container.replaceChildren();
    if (!evidence) {
      proofValue(container, "Primary guarded run", "");
      proofValue(container, "Concurrent private MCP run", "");
      proofValue(container, "Read-only snapshot", "");
      return;
    }
    proofValue(
      container,
      "Primary guarded run",
      evidence.primary_guarded_run?.certificate_sha256,
    );
    proofValue(
      container,
      "Concurrent private MCP run",
      evidence.concurrent_run?.certificate_sha256,
    );
    proofValue(
      container,
      "Read-only snapshot",
      evidence.read_only_snapshot?.matched_certificate_sha256,
    );
  }

  async function loadOverview() {
    try {
      const overview = await requestJson("/api/demo/overview");
      state.overview = overview;
      renderGraph(overview);
      renderCoordinatorProof(overview.coordinator_evidence);
    } catch (_error) {
      setText(byId("graph-count"), "Catalog metadata unavailable");
      byId("graph-grid").replaceChildren();
      renderCoordinatorProof(null);
    }
  }

  function renderPlan(plan) {
    const summary = byId("plan-summary");
    const values = summary.querySelectorAll("strong, code");
    setText(values[0], `${plan.decisions.length} deterministic decisions`);
    setText(values[1], shortHash(plan.plan_hash));
    values[1].title = plan.plan_hash;
    setText(values[2], "Required · exact hash");

    const body = byId("plan-table");
    body.replaceChildren(
      ...plan.decisions.map((decision) => {
        const row = document.createElement("tr");
        const artifact = document.createElement("td");
        const name = document.createElement("strong");
        setText(name, decision.artifact_name);
        const type = document.createElement("small");
        setText(type, decision.artifact_type.replaceAll("_", " "));
        artifact.append(name, type);
        const action = document.createElement("td");
        const actionBadge = document.createElement("span");
        actionBadge.className = `action-pill ${decision.action}`;
        setText(actionBadge, decision.action.replaceAll("_", " "));
        action.append(actionBadge);
        const selector = document.createElement("td");
        setText(selector, decision.selector_field || "not addressable");
        const status = document.createElement("td");
        const stateBadge = document.createElement("span");
        stateBadge.className = `state-pill ${decision.status}`;
        setText(stateBadge, decision.status);
        status.append(stateBadge);
        const reason = document.createElement("td");
        setText(reason, decision.reason);
        row.append(artifact, action, selector, status, reason);
        return row;
      }),
    );
    setText(byId("selector-token-preview"), maskedToken(plan.selector.token));
    byId("run-workflow").disabled = false;
    setText(
      byId("approval-note"),
      "Approval will be bound to the displayed SHA-256 plan hash.",
    );
  }

  async function buildPlan(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const button = byId("build-plan");
    button.disabled = true;
    button.textContent = "Building exact plan…";
    const selectorInput = byId("selector-value");
    const selectorValue = selectorInput.value;
    try {
      const plan = await requestJson("/api/demo/plan", {
        method: "POST",
        body: JSON.stringify({
          request_id: byId("request-id").value,
          selector_value: selectorValue,
        }),
      });
      state.plan = plan;
      state.selectorValue = selectorValue;
      selectorInput.value = "";
      selectorInput.placeholder = "Held in memory for approved run";
      renderPlan(plan);
      showToast("Impact plan built. The raw selector is no longer displayed.", "success");
      byId("plan").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      state.plan = null;
      state.selectorValue = null;
      showToast(error.message, "error");
    } finally {
      button.disabled = false;
      button.innerHTML = 'Build deterministic impact plan <span aria-hidden="true">→</span>';
    }
  }

  function setTimeline(phase, status) {
    const item = document.querySelector(`[data-phase="${phase}"]`);
    if (!item) return;
    item.dataset.state = status;
    setText(item.querySelector("b"), status.toUpperCase());
  }

  function resetTimeline() {
    document.querySelectorAll(".timeline-item").forEach((item) => {
      item.dataset.state = "waiting";
      setText(item.querySelector("b"), "WAITING");
    });
  }

  function animateTimeline() {
    const phases = ["context", "purge", "retrain", "verify", "writeback"];
    phases.forEach((phase, index) => {
      window.setTimeout(() => {
        if (!state.running) return;
        phases.slice(0, index).forEach((previous) => setTimeline(previous, "complete"));
        setTimeline(phase, "active");
      }, index * 850);
    });
  }

  function countStatuses(items) {
    return items.reduce(
      (counts, item) => {
        const status = item.status || "unknown";
        if (status === "verified") counts.verified += 1;
        else if (status === "failed") counts.failed += 1;
        else counts.limited += 1;
        return counts;
      },
      { verified: 0, failed: 0, limited: 0 },
    );
  }

  function renderVerification(items) {
    const counts = countStatuses(items);
    const metricValues = byId("verification-metrics").querySelectorAll("strong");
    setText(metricValues[0], counts.verified);
    setText(metricValues[1], counts.failed);
    setText(metricValues[2], counts.limited);
    const names = new Map((state.overview?.nodes || []).map((node) => [node.urn, node.name]));
    byId("verification-table").replaceChildren(
      ...items.map((item) => {
        const row = document.createElement("tr");
        const cells = [
          names.get(item.target_urn) || item.target_urn,
          String(item.action || "—").replaceAll("_", " "),
          item.before_count ?? "—",
          item.after_count ?? "—",
        ];
        cells.forEach((value) => {
          const cell = document.createElement("td");
          setText(cell, value);
          row.append(cell);
        });
        const status = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `state-pill ${item.status || "unknown"}`;
        setText(badge, item.status || "unknown");
        status.append(badge);
        row.append(status);
        return row;
      }),
    );
  }

  function addDownload(container, label, value) {
    if (!value?.download_url) return;
    const link = document.createElement("a");
    link.className = "button ghost";
    link.href = value.download_url;
    link.download = "";
    setText(link, label);
    container.append(link);
  }

  function renderCertificate(result) {
    byId("certificate-card").dataset.state =
      result.status === "failed" ? "failed" : "complete";
    setText(byId("certificate-status"), result.status.replaceAll("_", " "));
    setText(
      byId("certificate-description"),
      result.status === "verified_with_limitations"
        ? "All addressable descendants verified. The subject-unaddressable aggregate remains explicitly exempt."
        : "The certificate records the exact independently verified outcome.",
    );
    setText(byId("certificate-hash"), shortHash(result.certificate_hash));
    byId("certificate-hash").title = result.certificate_hash;
    setText(byId("certificate-plan-hash"), shortHash(result.plan_hash));
    byId("certificate-plan-hash").title = result.plan_hash;
    setText(
      byId("writeback-state"),
      result.datahub_required
        ? result.evidence.datahub_write_verified
          ? "verified immediate reread"
          : "required · no verified receipt"
        : "not required in local mode",
    );
    const actions = byId("certificate-actions");
    actions.replaceChildren();
    addDownload(actions, "Certificate JSON", result.evidence["certificate.json"]);
    addDownload(actions, "Certificate Markdown", result.evidence["certificate.md"]);
    addDownload(actions, "DataHub read receipt", result.evidence["datahub-read-receipt.json"]);
    addDownload(actions, "DataHub write receipt", result.evidence["datahub-write-receipt.json"]);
  }

  function markTimelineFailure() {
    const active = document.querySelector('.timeline-item[data-state="active"]');
    if (active) {
      active.dataset.state = "failed";
      setText(active.querySelector("b"), "FAILED CLOSED");
    }
  }

  async function executeWorkflow(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity() || !state.plan || !state.selectorValue || state.running) {
      if (!state.plan || !state.selectorValue) {
        showToast("Build a fresh plan before approval.", "error");
      }
      return;
    }
    state.running = true;
    const runButton = byId("run-workflow");
    runButton.disabled = true;
    runButton.textContent = "Executing guarded workflow…";
    resetTimeline();
    animateTimeline();
    try {
      const result = await requestJson("/api/demo/run", {
        method: "POST",
        body: JSON.stringify({
          request_id: state.plan.request_id,
          selector_value: state.selectorValue,
          plan_hash: state.plan.plan_hash,
          approver: byId("approver").value,
          approved: byId("approval-check").checked,
          reset_synthetic_estate: byId("reset-fixture").checked,
          require_datahub: byId("require-datahub").checked,
        }),
      });
      ["purge", "retrain", "verify"].forEach((phase) => setTimeline(phase, "complete"));
      setTimeline("context", result.datahub_required ? "complete" : "skipped");
      setTimeline("writeback", result.datahub_required ? "complete" : "skipped");
      state.selectorValue = null;
      renderVerification(result.items || []);
      renderCertificate(result);
      showToast("Workflow verified. Evidence certificate is ready.", "success");
      byId("certificate").scrollIntoView({ behavior: "smooth", block: "start" });
      await refreshReadiness();
    } catch (error) {
      markTimelineFailure();
      showToast(`${error.message} No success was recorded.`, "error");
    } finally {
      state.running = false;
      runButton.textContent = "Approve & execute guarded workflow";
      runButton.disabled = !state.plan || !state.selectorValue;
    }
  }

  function toggleSelector() {
    const input = byId("selector-value");
    const button = byId("toggle-selector");
    if (input.type === "password") {
      input.type = "text";
      button.textContent = "Hide";
      button.setAttribute("aria-label", "Hide selector");
      window.setTimeout(() => {
        input.type = "password";
        button.textContent = "Show";
        button.setAttribute("aria-label", "Show selector temporarily");
      }, 3000);
    } else {
      input.type = "password";
      button.textContent = "Show";
      button.setAttribute("aria-label", "Show selector temporarily");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("request-form").addEventListener("submit", buildPlan);
    byId("approval-form").addEventListener("submit", executeWorkflow);
    byId("toggle-selector").addEventListener("click", toggleSelector);
    byId("refresh-readiness").addEventListener("click", refreshReadiness);
    byId("request-id").addEventListener("input", () => {
      if (!state.plan) return;
      state.plan = null;
      state.selectorValue = null;
      byId("run-workflow").disabled = true;
      setText(byId("approval-note"), "The request changed. Build a fresh plan.");
    });
    Promise.allSettled([refreshReadiness(), loadOverview()]);
  });
})();
