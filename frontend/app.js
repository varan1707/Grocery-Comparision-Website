// Same-origin by default (the FastAPI backend serves this page). Set
// window.GROCERY_API_BASE_URL before this script to point at another backend.
const API_BASE_URL = (window.GROCERY_API_BASE_URL || "").replace(/\/$/, "");

const STATUS_LABELS = {
  live: "Live",
  demo: "Demo data",
  coming_soon: "Prices coming soon",
  not_configured: "Not configured",
  error: "Error",
};

async function fetchStores() {
  const res = await fetch(`${API_BASE_URL}/api/stores`);
  if (!res.ok) {
    throw new Error("Failed to fetch stores");
  }
  return res.json();
}

async function searchProducts(query, stores, zipCode) {
  const body = { query, stores };
  if (zipCode) body.zip_code = zipCode;
  const res = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const message = Array.isArray(detail.detail)
      ? detail.detail.map((d) => d.msg).join("; ")
      : detail.detail;
    throw new Error(message || "Search failed");
  }
  return res.json();
}

function badge(status) {
  const span = document.createElement("span");
  span.className = `badge badge-${status}`;
  span.textContent = STATUS_LABELS[status] || status;
  return span;
}

function isSafeUrl(url) {
  try {
    return ["http:", "https:"].includes(new URL(url).protocol);
  } catch {
    return false;
  }
}

function renderStores(stores) {
  const container = document.getElementById("stores-container");
  container.innerHTML = "";
  stores.forEach((store) => {
    const searchable = store.status === "live" || store.status === "demo";
    const wrapper = document.createElement("label");
    wrapper.className = "store-checkbox" + (searchable ? "" : " disabled");
    if (store.message) wrapper.title = store.message;

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = store.store_id;
    cb.checked = searchable;
    cb.disabled = !searchable;

    const span = document.createElement("span");
    span.textContent = store.store_name;

    wrapper.appendChild(cb);
    wrapper.appendChild(span);
    wrapper.appendChild(badge(store.status));
    container.appendChild(wrapper);
  });
}

function renderStoreStatus(statuses) {
  const list = document.getElementById("store-status");
  list.innerHTML = "";
  statuses
    .filter((s) => s.status !== "coming_soon")
    .forEach((s) => {
      const li = document.createElement("li");
      li.appendChild(document.createTextNode(`${s.store_name}: `));
      li.appendChild(badge(s.status));
      let text = "";
      if (s.status === "live" || s.status === "demo") {
        text = ` ${s.result_count} result(s)`;
        if (s.location) text += ` from ${s.location}`;
      } else if (s.message) {
        text = ` ${s.message}`;
      }
      li.appendChild(document.createTextNode(text));
      list.appendChild(li);
    });
}

function formatPrice(value) {
  return `$${Number(value).toFixed(2)}`;
}

function renderResults(products) {
  const tbody = document.getElementById("results-body");
  tbody.innerHTML = "";

  products.forEach((p) => {
    const tr = document.createElement("tr");

    const storeTd = document.createElement("td");
    storeTd.textContent = p.store_name;

    const nameTd = document.createElement("td");
    if (p.image_url && isSafeUrl(p.image_url)) {
      const img = document.createElement("img");
      img.src = p.image_url;
      img.alt = "";
      img.className = "product-thumb";
      img.loading = "lazy";
      img.addEventListener("error", () => img.remove());
      nameTd.appendChild(img);
    }
    if (p.product_url && isSafeUrl(p.product_url)) {
      const link = document.createElement("a");
      link.href = p.product_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = p.name;
      nameTd.appendChild(link);
    } else {
      nameTd.appendChild(document.createTextNode(p.name));
    }

    const priceTd = document.createElement("td");
    priceTd.textContent = formatPrice(p.price);
    if (p.regular_price) {
      const was = document.createElement("span");
      was.className = "price-was";
      was.textContent = formatPrice(p.regular_price);
      priceTd.appendChild(was);
    }

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
    priceTd.textContent = formatPrice(item.price);

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
  document.getElementById("total-cost").textContent = formatPrice(totalCost);
}

async function init() {
  const statusEl = document.getElementById("status");
  const searchBtn = document.getElementById("search-btn");
  const queryInput = document.getElementById("query");
  const zipInput = document.getElementById("zip");

  zipInput.value = localStorage.getItem("grocery.zip") || "";

  try {
    statusEl.textContent = "Loading stores…";
    renderStores(await fetchStores());
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = "Could not reach the backend. Is it running?";
    searchBtn.disabled = true;
    console.error(err);
    return;
  }

  async function runSearch() {
    const query = queryInput.value.trim();
    if (!query) {
      statusEl.textContent = "Enter an item to search.";
      return;
    }
    const zipCode = zipInput.value.trim();
    if (zipCode && !/^\d{5}$/.test(zipCode)) {
      statusEl.textContent = "ZIP code must be 5 digits.";
      return;
    }
    localStorage.setItem("grocery.zip", zipCode);

    const selectedStores = Array.from(
      document.querySelectorAll("#stores-container input[type=checkbox]")
    )
      .filter((cb) => cb.checked && !cb.disabled)
      .map((cb) => cb.value);
    if (selectedStores.length === 0) {
      statusEl.textContent = "No stores with live prices are selected.";
      return;
    }

    statusEl.textContent = "Searching…";
    searchBtn.disabled = true;

    try {
      const data = await searchProducts(query, selectedStores, zipCode);
      const results = data.results || [];
      renderResults(results);
      renderStoreStatus(data.stores || []);
      statusEl.textContent = `Found ${results.length} options.`;
    } catch (err) {
      console.error(err);
      statusEl.textContent = err.message || "Search failed.";
    } finally {
      searchBtn.disabled = false;
    }
  }

  searchBtn.addEventListener("click", runSearch);
  [queryInput, zipInput].forEach((el) =>
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") runSearch();
    })
  );
}

document.addEventListener("DOMContentLoaded", init);
