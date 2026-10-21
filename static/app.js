const $ = (sel) => document.querySelector(sel);

async function api(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  const resp = await fetch(url);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

function formatNumber(n) {
  if (n === null || n === undefined) return "-";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n);
}

function videoCard(item, index) {
  const card = document.createElement("div");
  card.className = "card";

  const cover = document.createElement("div");
  cover.className = "cover";
  if (index !== undefined) {
    const rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = "#" + (index + 1);
    cover.appendChild(rank);
  }
  if (item.cover) {
    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = item.cover;
    img.alt = "";
    cover.appendChild(img);
  }
  card.appendChild(cover);

  const body = document.createElement("div");
  body.className = "body";

  const title = document.createElement("div");
  title.className = "title";
  title.textContent = item.title_translated || item.title || "(không có tiêu đề)";
  if (item.title_translated && item.title && item.title_translated !== item.title) {
    const orig = document.createElement("div");
    orig.className = "orig";
    orig.textContent = item.title;
    title.appendChild(orig);
  }
  body.appendChild(title);

  const author = item.author || {};
  const stats = item.stats || {};
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `<span>@${author.handle || "?"}</span><span>▶ ${formatNumber(stats.views)}</span>`;
  body.appendChild(meta);

  if (item.url) {
    const link = document.createElement("a");
    link.className = "open";
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Mở trên TikTok ↗";
    body.appendChild(link);
  }

  card.appendChild(body);
  return card;
}

// --------------------------------------------------------------------------- //
// Tabs
// --------------------------------------------------------------------------- //
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    $("#panel-trending").classList.toggle("hidden", tab.dataset.tab !== "trending");
    $("#panel-search").classList.toggle("hidden", tab.dataset.tab !== "search");
  });
});

// --------------------------------------------------------------------------- //
// Khởi tạo dữ liệu metadata
// --------------------------------------------------------------------------- //
let META = null;

async function loadMeta() {
  META = await api("/api/countries");

  const trendCountry = $("#trend-country");
  META.trending.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.code;
    opt.textContent = `${c.name} (${c.code})`;
    trendCountry.appendChild(opt);
  });
  trendCountry.value = "VN";

  const searchCountries = $("#search-countries");
  META.search.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.code;
    opt.textContent = `${c.name} (${c.code})`;
    searchCountries.appendChild(opt);
  });
  ["VN", "US", "TH"].forEach((code) => {
    const opt = [...searchCountries.options].find((o) => o.value === code);
    if (opt) opt.selected = true;
  });

  const langSelects = [$("#search-languages"), $("#trend-target"), $("#search-target")];
  META.languages.forEach((l) => {
    langSelects.forEach((sel) => {
      const opt = document.createElement("option");
      opt.value = l.code;
      opt.textContent = `${l.name} (${l.code})`;
      sel.appendChild(opt);
    });
  });
  $("#trend-target").value = "vi";
  $("#search-target").value = "vi";
}

// --------------------------------------------------------------------------- //
// Trending
// --------------------------------------------------------------------------- //
$("#trend-load").addEventListener("click", async () => {
  const btn = $("#trend-load");
  const status = $("#trend-status");
  const results = $("#trend-results");
  btn.disabled = true;
  status.classList.remove("error");
  status.textContent = "Đang tải…";
  results.innerHTML = "";
  try {
    const data = await api("/api/trending", {
      country: $("#trend-country").value,
      period: $("#trend-period").value,
      translate: $("#trend-translate").checked,
      target_lang: $("#trend-target").value,
    });
    if (!data.items.length) {
      status.textContent = "Không có dữ liệu cho lựa chọn này.";
    } else {
      status.textContent = `${data.items.length} video · ${data.country_name} · ${data.period}`;
      data.items.forEach((item, i) => results.appendChild(videoCard(item, i)));
    }
  } catch (err) {
    status.classList.add("error");
    status.textContent = "Lỗi: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

// --------------------------------------------------------------------------- //
// Search
// --------------------------------------------------------------------------- //
$("#search-load").addEventListener("click", async () => {
  const btn = $("#search-load");
  const status = $("#search-status");
  const results = $("#search-results");
  const keyword = $("#search-keyword").value.trim();
  if (!keyword) {
    status.classList.add("error");
    status.textContent = "Nhập từ khóa trước đã.";
    return;
  }

  const countries = [...$("#search-countries").selectedOptions].map((o) => o.value).join(",");
  const languages = [...$("#search-languages").selectedOptions].map((o) => o.value).join(",");

  btn.disabled = true;
  status.classList.remove("error");
  status.textContent =
    "Đang tìm kiếm… Nếu TikTok yêu cầu captcha, hãy giải trong cửa sổ Chrome vừa mở — app sẽ tự tiếp tục.";
  results.innerHTML = "";

  try {
    const data = await api("/api/search", {
      keyword,
      countries,
      languages,
      translate: $("#search-translate").checked,
      target_lang: $("#search-target").value,
      limit: $("#search-limit").value,
    });
    results.innerHTML = "";
    let total = 0;
    if (data.hint) {
      const warn = document.createElement("div");
      warn.className = "status error";
      warn.textContent = data.hint;
      results.appendChild(warn);
    }
    data.groups.forEach((group) => {
      total += group.items.length;
      const heading = document.createElement("h3");
      heading.className = "group-title";
      const label = group.language_name || group.language || "";
      const searchUrl = group.search_url || `https://www.tiktok.com/search?q=${encodeURIComponent(group.keyword)}`;
      heading.innerHTML = `${group.country_name || group.country} <span class="badge">${label}</span> <span class="badge">“${group.keyword}”</span> <a class="search-link" href="${searchUrl}" target="_blank" rel="noreferrer" title="Mở link tìm kiếm trên TikTok">🔗 Xem trang search TikTok ↗</a>`;
      results.appendChild(heading);

      if (group.error) {
        const err = document.createElement("div");
        err.className = "status error";
        err.textContent = group.error;
        results.appendChild(err);
      }
      const grid = document.createElement("div");
      grid.className = "grid";
      group.items.forEach((item) => grid.appendChild(videoCard(item)));
      results.appendChild(grid);
    });
    const skipped = (data.skipped || []).length;
    status.textContent =
      `Tổng ${total} video trong ${data.groups.length} nhóm.` +
      (skipped ? ` Bỏ qua ${skipped} nhóm do dừng vì captcha.` : "");
  } catch (err) {
    status.classList.add("error");
    status.textContent = "Lỗi: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

loadMeta().catch((err) => {
  $("#trend-status").classList.add("error");
  $("#trend-status").textContent = "Không tải được metadata: " + err.message;
});
