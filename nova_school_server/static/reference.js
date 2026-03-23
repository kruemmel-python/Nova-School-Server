(function () {
  const body = document.body;
  if (!body || body.dataset.referencePage !== "true") {
    return;
  }

  const sidebarKey = "nova.reference.sidebarCollapsed";
  const wideKey = "nova.reference.wideReading";
  const sidebarButtons = Array.from(document.querySelectorAll("[data-reference-sidebar-toggle]"));
  const wideButton = document.querySelector("[data-reference-wide-toggle]");

  function applyState() {
    const sidebarCollapsed = body.classList.contains("reference-sidebar-collapsed");
    const wideReading = body.classList.contains("reference-wide-reading");

    for (const button of sidebarButtons) {
      button.textContent = sidebarCollapsed ? "Bereiche einblenden" : "Bereiche ausblenden";
      button.setAttribute("aria-expanded", String(!sidebarCollapsed));
    }

    if (wideButton) {
      wideButton.textContent = wideReading ? "Standardbreite" : "Breiter Lesemodus";
      wideButton.setAttribute("aria-pressed", String(wideReading));
    }
  }

  function setSidebarCollapsed(value) {
    body.classList.toggle("reference-sidebar-collapsed", value);
    localStorage.setItem(sidebarKey, value ? "1" : "0");
    applyState();
  }

  function setWideReading(value) {
    body.classList.toggle("reference-wide-reading", value);
    localStorage.setItem(wideKey, value ? "1" : "0");
    applyState();
  }

  if (localStorage.getItem(sidebarKey) === "1") {
    body.classList.add("reference-sidebar-collapsed");
  }
  if (localStorage.getItem(wideKey) === "1") {
    body.classList.add("reference-wide-reading");
  }
  applyState();

  for (const button of sidebarButtons) {
    button.addEventListener("click", () => {
      setSidebarCollapsed(!body.classList.contains("reference-sidebar-collapsed"));
    });
  }

  if (wideButton) {
    wideButton.addEventListener("click", () => {
      setWideReading(!body.classList.contains("reference-wide-reading"));
    });
  }
})();
