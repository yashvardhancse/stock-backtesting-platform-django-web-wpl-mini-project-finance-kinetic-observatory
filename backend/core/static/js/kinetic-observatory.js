(function ($) {
  "use strict";

  const KINETIC = window.KINETIC || {};
  const chartInstances = {};
  const dataState = {
    page: 1,
    pageSize: 100,
    sortBy: "Date",
    sortDir: "asc",
    datasetId: KINETIC.latestDatasetId || "",
    search: "",
  };

  function getCookie(name) {
    const cookieValue = document.cookie.split("; ").find((row) => row.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=").slice(1).join("=")) : "";
  }

  function setLoading(active) {
    $("#loadingOverlay").toggleClass("d-none", !active);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function showToast(message, variant = "info", title = "Kinetic Observatory") {
    const toastId = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const borderClass = variant === "success" ? "border-success" : variant === "danger" ? "border-danger" : "border-info";
    const toastHtml = `
      <div id="${toastId}" class="toast ${borderClass}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="3500">
        <div class="toast-header">
          <strong class="me-auto">${escapeHtml(title)}</strong>
          <small>${new Date().toLocaleTimeString()}</small>
          <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${escapeHtml(message)}</div>
      </div>`;
    $("#toastContainer").append(toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    toastElement.addEventListener("hidden.bs.toast", () => $(toastElement).remove());
  }

  function formatMoney(value) {
    const numeric = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(numeric);
  }

  function formatNumber(value, fractionDigits = 2) {
    const numeric = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    }).format(numeric);
  }

  function destroyChart(canvasId) {
    if (chartInstances[canvasId]) {
      chartInstances[canvasId].destroy();
      delete chartInstances[canvasId];
    }
  }

  function buildLineDataset(label, data, color, extra = {}) {
    return $.extend(
      true,
      {
        label,
        data,
        borderColor: color,
        backgroundColor: color,
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2,
        fill: false,
        spanGaps: true,
      },
      extra,
    );
  }

  function buildMarkerDataset(label, data, color) {
    return {
      label,
      data,
      borderColor: color,
      backgroundColor: color,
      pointRadius: 6,
      pointHoverRadius: 8,
      pointStyle: label === "BUY" ? "triangle" : "rectRot",
      showLine: false,
      borderWidth: 0,
      spanGaps: true,
    };
  }

  function createChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") {
      return null;
    }
    destroyChart(canvasId);
    chartInstances[canvasId] = new Chart(canvas.getContext("2d"), config);
    return chartInstances[canvasId];
  }

  function alignSignals(labels, signals, type) {
    const points = labels.map(() => null);
    const indexMap = new Map(labels.map((label, index) => [label, index]));
    (signals || []).forEach((signal) => {
      if ((signal.type || "").toUpperCase() !== type.toUpperCase()) {
        return;
      }
      const index = indexMap.get(signal.date);
      if (index !== undefined) {
        points[index] = Number(signal.price);
      }
    });
    return points;
  }

  function updateSummary(summary) {
    if (!summary) {
      return;
    }
    if (document.getElementById("summaryProfit")) {
      $("#summaryProfit").text(formatMoney(summary.total_profit || 0));
    }
    if (document.getElementById("summaryTrades")) {
      $("#summaryTrades").text(summary.trade_count ?? 0);
    }
    if (document.getElementById("summaryWinRate")) {
      $("#summaryWinRate").text(`${formatNumber(summary.win_rate || 0)}%`);
    }
    if (document.getElementById("summarySharpe")) {
      $("#summarySharpe").text(formatNumber(summary.sharpe_ratio || 0, 2));
    }
    if (document.getElementById("resultSummaryProfit")) {
      $("#resultSummaryProfit").text(formatMoney(summary.total_profit || 0));
    }
    if (document.getElementById("resultSummaryTrades")) {
      $("#resultSummaryTrades").text(summary.trade_count ?? 0);
    }
    if (document.getElementById("resultSummaryWinRate")) {
      $("#resultSummaryWinRate").text(`${formatNumber(summary.win_rate || 0)}%`);
    }
    if (document.getElementById("resultSummarySharpe")) {
      $("#resultSummarySharpe").text(formatNumber(summary.sharpe_ratio || 0, 2));
    }
  }

  function renderTradeTable(trades) {
    const tableBody = $("#tradeLogTable tbody");
    if (!tableBody.length) {
      return;
    }
    if (!trades || !trades.length) {
      tableBody.html('<tr><td colspan="6" class="text-center text-secondary py-4">No closed trades were generated.</td></tr>');
      return;
    }
    const rows = trades
      .map((trade) => {
        const profitClass = Number(trade.profit || 0) >= 0 ? "text-success" : "text-danger";
        return `
          <tr>
            <td>${escapeHtml(trade.entry_date || "-")}</td>
            <td>${escapeHtml(trade.exit_date || "-")}</td>
            <td><span class="signal-chip ${trade.side === "LONG" ? "signal-chip-success" : "signal-chip-warning"}">${escapeHtml(trade.side || "-")}</span></td>
            <td class="text-end">${formatMoney(trade.entry_price || 0)}</td>
            <td class="text-end">${formatMoney(trade.exit_price || 0)}</td>
            <td class="text-end ${profitClass}">${formatMoney(trade.profit || 0)}</td>
          </tr>`;
      })
      .join("");
    tableBody.html(rows);
  }

  function renderPreviewTable(rows) {
    const tableBody = $("#uploadPreviewTable tbody");
    if (!tableBody.length) {
      return;
    }
    if (!rows || !rows.length) {
      tableBody.html('<tr><td colspan="6" class="text-center text-secondary py-4">No preview rows returned.</td></tr>');
      return;
    }
    const html = rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.Date || row.date || "-")}</td>
            <td class="text-end">${formatMoney(row.Open || row.open || 0)}</td>
            <td class="text-end">${formatMoney(row.High || row.high || 0)}</td>
            <td class="text-end">${formatMoney(row.Low || row.low || 0)}</td>
            <td class="text-end">${formatMoney(row.Close || row.close || 0)}</td>
            <td class="text-end">${formatNumber(row.Volume || row.volume || 0, 2)}</td>
          </tr>`,
      )
      .join("");
    tableBody.html(html);
  }

  function renderDataTable(rows) {
    const tableBody = $("#dataTable tbody");
    if (!tableBody.length) {
      return;
    }
    if (!rows || !rows.length) {
      tableBody.html('<tr><td colspan="6" class="text-center text-secondary py-4">No rows match the current filter.</td></tr>');
      return;
    }
    const html = rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.Date || row.date || "-")}</td>
            <td class="text-end">${formatMoney(row.Open || row.open || 0)}</td>
            <td class="text-end">${formatMoney(row.High || row.high || 0)}</td>
            <td class="text-end">${formatMoney(row.Low || row.low || 0)}</td>
            <td class="text-end">${formatMoney(row.Close || row.close || 0)}</td>
            <td class="text-end">${formatNumber(row.Volume || row.volume || 0, 2)}</td>
          </tr>`,
      )
      .join("");
    tableBody.html(html);
  }

  function renderPriceChart(result) {
    const priceData = result.price_data || [];
    if (!priceData.length) {
      destroyChart("priceChart");
      return;
    }

    const indicators = result.indicators || {};
    const labels = priceData.map((row) => row.Date || row.date || row.timestamp || "");
    const closeSeries = priceData.map((row) => Number(row.Close ?? row.close ?? 0));

    const datasets = [buildLineDataset("Close", closeSeries, "#85a6ff", { borderWidth: 2 })];

    if (indicators.sma_short) {
      datasets.push(buildLineDataset("SMA Short", indicators.sma_short.map((value) => (value == null ? null : Number(value))), "#52f1c3"));
    }
    if (indicators.sma_long) {
      datasets.push(buildLineDataset("SMA Long", indicators.sma_long.map((value) => (value == null ? null : Number(value))), "#ffcb6b"));
    }
    if (indicators.ema_short) {
      datasets.push(buildLineDataset("EMA Short", indicators.ema_short.map((value) => (value == null ? null : Number(value))), "#79cfff", { borderDash: [8, 6] }));
    }
    if (indicators.ema_long) {
      datasets.push(buildLineDataset("EMA Long", indicators.ema_long.map((value) => (value == null ? null : Number(value))), "#c58cff", { borderDash: [8, 6] }));
    }
    if (indicators.vwap) {
      datasets.push(buildLineDataset("VWAP", indicators.vwap.map((value) => (value == null ? null : Number(value))), "#f1d36f", { borderDash: [2, 4] }));
    }
    if (indicators.bb_lower && indicators.bb_upper) {
      datasets.push(buildLineDataset("Bollinger Lower", indicators.bb_lower.map((value) => (value == null ? null : Number(value))), "rgba(133, 166, 255, 0.55)", { borderDash: [6, 6], borderWidth: 1 }));
      datasets.push(buildLineDataset("Bollinger Upper", indicators.bb_upper.map((value) => (value == null ? null : Number(value))), "rgba(133, 166, 255, 0.75)", { borderDash: [6, 6], borderWidth: 1, fill: "-1", backgroundColor: "rgba(133, 166, 255, 0.08)" }));
    }

    const buyMarkers = alignSignals(labels, result.signals, "BUY");
    const sellMarkers = alignSignals(labels, result.signals, "SELL");
    datasets.push(buildMarkerDataset("BUY", buyMarkers, "#52f1c3"));
    datasets.push(buildMarkerDataset("SELL", sellMarkers, "#ff6e84"));

    createChart("priceChart", {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            labels: {
              color: "#dfe5fc",
              usePointStyle: true,
              boxWidth: 10,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: "#98a7cb", maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
            grid: { color: "rgba(145, 166, 214, 0.08)" },
          },
          y: {
            ticks: { color: "#98a7cb" },
            grid: { color: "rgba(145, 166, 214, 0.08)" },
          },
        },
      },
    });
  }

  function renderRsiChart(result) {
    const indicators = result.indicators || {};
    const rsi = indicators.rsi || [];
    if (!rsi.length) {
      destroyChart("rsiChart");
      return;
    }
    const labels = rsi.map((_, index) => index + 1);
    const overbought = labels.map(() => 70);
    const oversold = labels.map(() => 30);

    createChart("rsiChart", {
      type: "line",
      data: {
        labels,
        datasets: [
          buildLineDataset("RSI", rsi.map((value) => (value == null ? null : Number(value))), "#52f1c3"),
          buildLineDataset("Overbought", overbought, "#ff6e84", { borderDash: [6, 6], borderWidth: 1 }),
          buildLineDataset("Oversold", oversold, "#85a6ff", { borderDash: [6, 6], borderWidth: 1 }),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#dfe5fc" } } },
        scales: {
          x: { ticks: { color: "#98a7cb", display: false }, grid: { color: "rgba(145, 166, 214, 0.06)" } },
          y: { min: 0, max: 100, ticks: { color: "#98a7cb" }, grid: { color: "rgba(145, 166, 214, 0.08)" } },
        },
      },
    });
  }

  function renderMacdChart(result) {
    const indicators = result.indicators || {};
    const macd = indicators.macd || [];
    if (!macd.length) {
      destroyChart("macdChart");
      return;
    }
    const labels = macd.map((_, index) => index + 1);
    const hist = indicators.macd_hist || [];
    const histogramColors = hist.map((value) => (Number(value || 0) >= 0 ? "rgba(82, 241, 195, 0.8)" : "rgba(255, 110, 132, 0.8)"));

    createChart("macdChart", {
      data: {
        labels,
        datasets: [
          buildLineDataset("MACD", macd.map((value) => (value == null ? null : Number(value))), "#85a6ff"),
          buildLineDataset("Signal", (indicators.macd_signal || []).map((value) => (value == null ? null : Number(value))), "#ffcb6b"),
          {
            type: "bar",
            label: "Histogram",
            data: hist.map((value) => Number(value || 0)),
            backgroundColor: histogramColors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#dfe5fc" } } },
        scales: {
          x: { ticks: { color: "#98a7cb", display: false }, grid: { color: "rgba(145, 166, 214, 0.06)" } },
          y: { ticks: { color: "#98a7cb" }, grid: { color: "rgba(145, 166, 214, 0.08)" } },
        },
      },
    });
  }

  function renderEquityChart(result) {
    const curve = result.equity_curve || [];
    if (!curve.length) {
      destroyChart("equityChart");
      return;
    }
    const labels = curve.map((row) => row.date || row.timestamp || "");
    const equity = curve.map((row) => Number(row.equity || 0));

    createChart("equityChart", {
      type: "line",
      data: {
        labels,
        datasets: [
          buildLineDataset("Equity", equity, "#52f1c3", {
            fill: true,
            backgroundColor: "rgba(82, 241, 195, 0.12)",
          }),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#dfe5fc" } } },
        scales: {
          x: { ticks: { color: "#98a7cb", display: false }, grid: { color: "rgba(145, 166, 214, 0.06)" } },
          y: { ticks: { color: "#98a7cb" }, grid: { color: "rgba(145, 166, 214, 0.08)" } },
        },
      },
    });
  }

  function renderMonteCarloChart(result) {
    const monteCarlo = result.monte_carlo || {};
    const histogram = monteCarlo.histogram || {};
    const bins = histogram.bins || [];
    const counts = histogram.counts || [];
    if (!bins.length || !counts.length) {
      destroyChart("monteCarloChart");
      return;
    }
    const labels = [];
    for (let index = 0; index < counts.length; index += 1) {
      const start = bins[index];
      const end = bins[index + 1];
      labels.push(`${formatMoney(start)} - ${formatMoney(end)}`);
    }

    createChart("monteCarloChart", {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Final portfolio distribution",
            data: counts.map((count) => Number(count || 0)),
            borderColor: "#85a6ff",
            backgroundColor: "rgba(133, 166, 255, 0.55)",
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#dfe5fc" } } },
        scales: {
          x: { ticks: { color: "#98a7cb", maxRotation: 0, autoSkip: true }, grid: { color: "rgba(145, 166, 214, 0.06)" } },
          y: { ticks: { color: "#98a7cb" }, grid: { color: "rgba(145, 166, 214, 0.08)" } },
        },
      },
    });
  }

  function renderResultBundle(result) {
    if (!result) {
      return;
    }
    updateSummary(result.metrics || result.summary || {});
    renderTradeTable(result.trades || []);
    renderPriceChart(result);
    renderRsiChart(result);
    renderMacdChart(result);
    renderEquityChart(result);
    renderMonteCarloChart(result);

    if (result.paper_trading) {
      if (document.getElementById("paperBalance")) {
        $("#paperBalance").text(formatMoney(result.paper_trading.final_balance || 0));
      }
      if (document.getElementById("paperPnl")) {
        $("#paperPnl").text(formatMoney(result.paper_trading.realized_pnl || 0));
      }
    }

    if (document.getElementById("chartStatus")) {
      $("#chartStatus").text("Analysis complete");
    }
  }

  function refreshDatasetOptions(dataset) {
    if (!dataset) {
      return;
    }
    const optionMarkup = `<option value="${dataset.id}" selected>${escapeHtml(dataset.original_name)}</option>`;
    ["#backtestDatasetSelect", "#dataDatasetSelect"].forEach((selector) => {
      const element = $(selector);
      if (!element.length) {
        return;
      }
      const existing = element.find(`option[value="${dataset.id}"]`);
      if (!existing.length) {
        element.append(optionMarkup);
      }
      element.val(String(dataset.id));
    });
    $("#backtestDatasetId").val(String(dataset.id));
    dataState.datasetId = String(dataset.id);
  }

  function loadLatestResult(resultId) {
    const params = resultId ? { result_id: resultId } : {};
    setLoading(true);
    $.getJSON(KINETIC.endpoints.results, params)
      .done((response) => {
        if (response.success) {
          renderResultBundle(response.result);
          updateSummary(response.summary || {});
          if (response.result && response.result.dataset) {
            refreshDatasetOptions(response.result.dataset);
          }
          if (document.getElementById("paperBalance") && response.result && response.result.paper_trading) {
            $("#paperBalance").text(formatMoney(response.result.paper_trading.final_balance || 0));
            $("#paperPnl").text(formatMoney(response.result.paper_trading.realized_pnl || 0));
          }
        }
      })
      .fail((xhr) => {
        const message = xhr.responseJSON?.message || "Unable to load the latest results.";
        showToast(message, "danger");
      })
      .always(() => setLoading(false));
  }

  function loadDataTable() {
    if (!$("#dataTable").length) {
      return;
    }
    if (!dataState.datasetId) {
      dataState.datasetId = $("#dataDatasetSelect").val() || KINETIC.latestDatasetId || "";
    }
    if (!dataState.datasetId) {
      $("#dataMeta").text("Upload a dataset to populate this table");
      return;
    }
    setLoading(true);
    $.getJSON(KINETIC.endpoints.data, {
      dataset_id: dataState.datasetId,
      search: dataState.search,
      sort_by: dataState.sortBy,
      sort_dir: dataState.sortDir,
      page: dataState.page,
      page_size: dataState.pageSize,
    })
      .done((response) => {
        if (response.success) {
          renderDataTable(response.rows || []);
          $("#dataMeta").text(`Showing ${response.total_rows || 0} rows · Page ${response.page || 1}`);
          $("#dataPrevPage").prop("disabled", (response.page || 1) <= 1);
          $("#dataNextPage").prop("disabled", (response.page || 1) * (response.page_size || dataState.pageSize) >= (response.total_rows || 0));
        }
      })
      .fail((xhr) => {
        const message = xhr.responseJSON?.message || "Failed to load dataset rows.";
        showToast(message, "danger");
      })
      .always(() => setLoading(false));
  }

  function bindUploadForm() {
    const form = $("#uploadForm");
    if (!form.length) {
      return;
    }

    const fileInput = form.find('input[type="file"]');
    const labelInput = form.find('input[name="label"]');
    const dropzone = $("#csvDropzone");

    dropzone.on("click", () => fileInput.trigger("click"));

    fileInput.on("change", function () {
      if (this.files && this.files[0]) {
        dropzone.find(".dropzone-title").text(this.files[0].name);
        dropzone.addClass("dragover");
        setTimeout(() => dropzone.removeClass("dragover"), 450);
      }
    });

    dropzone.on("dragover dragenter", function (event) {
      event.preventDefault();
      event.stopPropagation();
      $(this).addClass("dragover");
    });

    dropzone.on("dragleave dragend drop", function (event) {
      event.preventDefault();
      event.stopPropagation();
      $(this).removeClass("dragover");
      if (event.type === "drop" && event.originalEvent.dataTransfer.files.length) {
        fileInput[0].files = event.originalEvent.dataTransfer.files;
        dropzone.find(".dropzone-title").text(event.originalEvent.dataTransfer.files[0].name);
      }
    });

    form.on("submit", function (event) {
      event.preventDefault();
      const file = fileInput[0].files[0];
      if (!file) {
        showToast("Choose a CSV or Excel file before uploading.", "danger");
        return;
      }
      if (!/(\.csv|\.xlsx|\.xls)$/i.test(file.name)) {
        showToast("Only CSV and Excel files are supported.", "danger");
        return;
      }

      const formData = new FormData(this);
      setLoading(true);
      $.ajax({
        url: KINETIC.endpoints.upload,
        method: "POST",
        data: formData,
        processData: false,
        contentType: false,
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      })
        .done((response) => {
          if (response.success) {
            showToast(response.message || "Upload complete.", "success");
            renderPreviewTable(response.preview_rows || []);
            refreshDatasetOptions(response.dataset);
            if (document.getElementById("dataMeta")) {
              $("#dataMeta").text(`Uploaded ${response.dataset.row_count} cleaned rows`);
            }
            if (document.getElementById("chartStatus")) {
              $("#chartStatus").text("Awaiting backtest run");
            }
          }
        })
        .fail((xhr) => {
          const message = xhr.responseJSON?.message || "Upload failed.";
          showToast(message, "danger");
        })
        .always(() => setLoading(false));
    });

    if (labelInput.length) {
      labelInput.on("input", function () {
        dropzone.find(".dropzone-copy").text(this.value ? `Dataset label: ${this.value}` : "Or choose a file using the input above.");
      });
    }
  }

  function bindBacktestForm() {
    const form = $("#backtestForm");
    if (!form.length) {
      return;
    }

    const datasetSelect = $("#backtestDatasetSelect");
    const hiddenDatasetInput = $("#backtestDatasetId");
    const syncDatasetId = () => {
      const value = datasetSelect.val() || KINETIC.latestDatasetId || "";
      hiddenDatasetInput.val(value);
      dataState.datasetId = value;
      return value;
    };

    datasetSelect.on("change", syncDatasetId);
    syncDatasetId();

    form.on("submit", function (event) {
      event.preventDefault();
      const datasetId = syncDatasetId();
      if (!datasetId) {
        showToast("Upload a dataset before running the strategy.", "danger");
        return;
      }

      const formData = new FormData(this);
      setLoading(true);
      $.ajax({
        url: KINETIC.endpoints.backtest,
        method: "POST",
        data: formData,
        processData: false,
        contentType: false,
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      })
        .done((response) => {
          if (response.success) {
            showToast(response.message || "Backtest complete.", "success");
            renderResultBundle(response);
            updateSummary(response.summary || response.metrics || {});
            if (response.paper_trading) {
              $("#paperBalance").text(formatMoney(response.paper_trading.final_balance || 0));
              $("#paperPnl").text(formatMoney(response.paper_trading.realized_pnl || 0));
            }
            if (response.dataset) {
              refreshDatasetOptions(response.dataset);
            }
            KINETIC.latestResultId = String(response.result_id || "");
            $("body").attr("data-latest-result-id", KINETIC.latestResultId);
            $("#chartStatus").text("Analysis complete");
          }
        })
        .fail((xhr) => {
          const message = xhr.responseJSON?.message || "Backtest failed.";
          showToast(message, "danger");
        })
        .always(() => setLoading(false));
    });
  }

  function bindDataPage() {
    if (!$("#dataTable").length) {
      return;
    }

    const datasetSelect = $("#dataDatasetSelect");
    const searchInput = $("#dataSearchInput");
    const sortSelect = $("#dataSortSelect");
    const sortDirSelect = $("#dataSortDirSelect");
    let searchTimer = null;

    const syncControls = () => {
      dataState.datasetId = datasetSelect.val() || KINETIC.latestDatasetId || "";
      dataState.sortBy = sortSelect.val() || "Date";
      dataState.sortDir = sortDirSelect.val() || "asc";
      dataState.page = 1;
      loadDataTable();
    };

    datasetSelect.on("change", syncControls);
    sortSelect.on("change", syncControls);
    sortDirSelect.on("change", syncControls);

    searchInput.on("input", function () {
      window.clearTimeout(searchTimer);
      const value = $(this).val();
      searchTimer = window.setTimeout(() => {
        dataState.search = value;
        dataState.page = 1;
        loadDataTable();
      }, 250);
    });

    $("#dataPrevPage").on("click", function () {
      if (dataState.page > 1) {
        dataState.page -= 1;
        loadDataTable();
      }
    });

    $("#dataNextPage").on("click", function () {
      dataState.page += 1;
      loadDataTable();
    });

    $("#dataTable thead th[data-sort]").on("click", function () {
      const sortBy = $(this).data("sort");
      if (dataState.sortBy === sortBy) {
        dataState.sortDir = dataState.sortDir === "asc" ? "desc" : "asc";
      } else {
        dataState.sortBy = sortBy;
        dataState.sortDir = "asc";
      }
      sortSelect.val(dataState.sortBy);
      sortDirSelect.val(dataState.sortDir);
      loadDataTable();
    });

    loadDataTable();
  }

  function bindResultsPage() {
    if (!document.getElementById("priceChart") || !window.KINETIC.latestResultId) {
      if (document.getElementById("chartStatus") && !window.KINETIC.latestResultId) {
        $("#chartStatus").text("No stored result yet");
      }
      return;
    }
    loadLatestResult(window.KINETIC.latestResultId);
  }

  function bindGlobalSearch() {
    const globalSearch = $("#globalSearchInput");
    if (!globalSearch.length || !$("#dataSearchInput").length) {
      return;
    }
    globalSearch.on("input", function () {
      $("#dataSearchInput").val($(this).val()).trigger("input");
    });
  }

  $(function () {
    $.ajaxSetup({ headers: { "X-CSRFToken": getCookie("csrftoken") } });
    bindUploadForm();
    bindBacktestForm();
    bindDataPage();
    bindResultsPage();
    bindGlobalSearch();
  });
})(jQuery);
