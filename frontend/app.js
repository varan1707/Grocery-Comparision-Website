const API_BASE_URL = "http://localhost:8000";

async function fetchStores() {
  const res = await fetch(`${API_BASE_URL}/api/stores`);
  if (!res.ok) {
    throw new Error("Failed to fetch stores");
  }
  return res.json();
}

async function searchProducts(query, stores) {
  const res = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, stores }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "Search failed");
  }
  return res.json();
}

function renderStores(storesMap) {
  const container = document.getElementById("stores-container");
  container.innerHTML = "";
  Object.entries(storesMap).forEach(([id, name]) => {
    const wrapper = document.createElement("label");
    wrapper.className = "store-checkbox";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = id;
    cb.checked = true;

    const span = document.createElement("span");
    span.textContent = name;

    wrapper.appendChild(cb);
    wrapper.appendChild(span);
    container.appendChild(wrapper);
  });
}

function renderResults(products) {
  const tbody = document.getElementById("results-body");
  tbody.innerHTML = "";

  products.forEach((p, idx) => {
    const tr = document.createElement("tr");

    const storeTd = document.createElement("td");
    storeTd.textContent = p.store_name;

    const nameTd = document.createElement("td");
    if (p.product_url) {
      const link = document.createElement("a");
      link.href = p.product_url;
      link.target = "_blank";
      link.textContent = p.name;
      nameTd.appendChild(link);
    } else {
      nameTd.textContent = p.name;
    }

    const priceTd = document.createElement("td");
    priceTd.textContent = `$${p.price.toFixed(2)}`;

    const unitTd = document.createElement("td");
    unitTd.textContent = p.unit || "";

    const actionTd = document.createElement("td");
    const addBtn = document.createElement("button");
    addBtn.textContent = "Add to list";
    addBtn.addEventListener("click", () => addToList(p));
    actionTd.appendChild(addBtn);

    tr.appendChild(storeTd);
    tr.appendChild(nameTd);
    tr.appendChild(priceTd);
    tr.appendChild(unitTd);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });
}

const comparisonList = [];

function addToList(item) {
  comparisonList.push(item);
  renderList();
}

function removeFromList(index) {
  comparisonList.splice(index, 1);
  renderList();
}

function renderList() {
  const tbody = document.getElementById("list-body");
  tbody.innerHTML = "";

  comparisonList.forEach((item, index) => {
    const tr = document.createElement("tr");

    const itemTd = document.createElement("td");
    itemTd.textContent = item.name;

    const storeTd = document.createElement("td");
    storeTd.textContent = item.store_name;

    const priceTd = document.createElement("td");
    priceTd.textContent = `$${item.price.toFixed(2)}`;

    const actionTd = document.createElement("td");
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => removeFromList(index));
    actionTd.appendChild(removeBtn);

    tr.appendChild(itemTd);
    tr.appendChild(storeTd);
    tr.appendChild(priceTd);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });

  const totalItems = comparisonList.length;
  const totalCost = comparisonList.reduce((sum, item) => sum + item.price, 0);

  document.getElementById("total-items").textContent = String(totalItems);
  document.getElementById("total-cost").textContent = `$${totalCost.toFixed(2)}`;
}

async function init() {
  const statusEl = document.getElementById("status");
  const searchBtn = document.getElementById("search-btn");
  const queryInput = document.getElementById("query");

  try {
    statusEl.textContent = "Loading stores…";
    const stores = await fetchStores();
    renderStores(stores);
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = "Failed to load stores; using defaults.";
    console.error(err);
  }

  searchBtn.addEventListener("click", async () => {
    const query = queryInput.value.trim();
    if (!query) {
      statusEl.textContent = "Enter an item to search.";
      return;
    }

    const storeCheckboxes = document.querySelectorAll(
      "#stores-container input[type=checkbox]"
    );
    const selectedStores = Array.from(storeCheckboxes)
      .filter((cb) => cb.checked)
      .map((cb) => cb.value);

    statusEl.textContent = "Searching…";
    searchBtn.disabled = true;

    try {
      const data = await searchProducts(query, selectedStores);
      renderResults(data.results || []);
      statusEl.textContent = `Found ${data.results.length} options.`;
    } catch (err) {
      console.error(err);
      statusEl.textContent = err.message || "Search failed.";
    } finally {
      searchBtn.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", init);


