(function ($) {
  "use strict";

  const KINETIC = window.KINETIC || {};
  const dataState = {
    datasetId: KINETIC.latestDatasetId || "",
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

  function extractErrorMessage(xhr, fallback = "Request failed.") {
    const payload = xhr?.responseJSON || {};
    if (payload.error) {
      return payload.error;
    }
    if (payload.message) {
      return payload.message;
    }
    if (Array.isArray(payload.errors)) {
      return payload.errors.join(" | ");
    }
    if (payload.errors && typeof payload.errors === "object") {
      const collected = [];
      Object.values(payload.errors).forEach((items) => {
        if (Array.isArray(items)) {
          items.forEach((item) => {
            if (typeof item === "string") {
              collected.push(item);
            } else if (item && typeof item === "object" && item.message) {
              collected.push(item.message);
            }
          });
        }
      });
      if (collected.length) {
        return collected.join(" | ");
      }
    }
    return fallback;
  }

  function formatMoney(value) {
    const numeric = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(numeric);
  }

  function formatMoneyWhole(value) {
    const numeric = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(numeric);
  }

  function formatNumber(value, fractionDigits = 2) {
    const numeric = Number(value || 0);
    return new Intl.NumberFormat("en-IN", {
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    }).format(numeric);
  }

  function updateSummary(totalProfit, numTrades, winPercent = 0, initialBalance = 100000) {
    if (document.getElementById("profit")) {
      $("#profit").text(formatMoney(totalProfit));
    }
    if (document.getElementById("trades")) {
      $("#trades").text(numTrades ?? 0);
    }
    if (document.getElementById("resultProfit")) {
      const profitElement = $("#resultProfit");
      const numericProfit = Number(totalProfit || 0);
      if (numericProfit < 0) {
        profitElement.text(`Loss ${formatMoney(Math.abs(numericProfit))}`);
        profitElement.addClass("text-danger");
      } else {
        profitElement.text(`Profit ${formatMoney(numericProfit)}`);
        profitElement.removeClass("text-danger");
      }
    }
    if (document.getElementById("resultTrades")) {
      $("#resultTrades").text(numTrades ?? 0);
    }
    if (document.getElementById("resultWinPercent")) {
      $("#resultWinPercent").text(`${formatNumber(winPercent ?? 0, 2)}%`);
    }
    if (document.getElementById("resultCapital")) {
      $("#resultCapital").text(formatMoneyWhole(initialBalance ?? 100000));
    }
  }

  function renderTrades(trades) {
    let html = "";

    (trades || []).forEach((t) => {
      const entryTime = t.entry_time || t.entry_date || "-";
      const exitTime = t.exit_time || t.exit_date || "-";
      const buyPrice = Number(t.buy_price ?? t.entry_price ?? 0);
      const sellPrice = Number(t.sell_price ?? t.exit_price ?? 0);
      const quantity = Number(t.quantity ?? 1);
      const capitalAllocated = Number(t.capital_allocated ?? t.capital_used ?? buyPrice * quantity);
      const profit = Number(t.profit ?? 0);

        const isProfit = profit >= 0;
        const pnlLabel = isProfit ? `Profit ${formatMoney(Math.abs(profit))}` : `Loss ${formatMoney(Math.abs(profit))}`;

        html += `
        <tr>
            <td>${escapeHtml(entryTime)}</td>
            <td>${escapeHtml(exitTime)}</td>
            <td class="text-end">${formatNumber(buyPrice, 2)}</td>
            <td class="text-end">${formatNumber(sellPrice, 2)}</td>
            <td class="text-end">${formatNumber(quantity, 0)}</td>
            <td class="text-end">${formatMoney(capitalAllocated)}</td>
          <td class="text-end" style="color:${isProfit ? "#52f1c3" : "#ff6e84"}">
            ${pnlLabel}
            </td>
        </tr>`;
    });

    if (!html) {
      html = '<tr><td colspan="7" class="text-center text-secondary py-4">No trades generated for the selected run.</td></tr>';
    }

    $("#tradeTable").html(html);
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

  function refreshDatasetOptions(dataset) {
    if (!dataset) {
      return;
    }
    const optionMarkup = `<option value="${dataset.id}" selected>${escapeHtml(dataset.original_name)}</option>`;
    ["#backtestDatasetSelect"].forEach((selector) => {
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
          updateSummary(
            response.total_profit || 0,
            response.num_trades || 0,
            response.win_percent || 0,
            response.initial_balance || 100000,
          );
          renderTrades(response.trades || []);
          if (response.dataset) {
            refreshDatasetOptions(response.dataset);
          }
          if (response.result_id) {
            KINETIC.latestResultId = String(response.result_id);
            $("body").attr("data-latest-result-id", KINETIC.latestResultId);
          }
        }
      })
      .fail((xhr) => {
        const message = xhr.responseJSON?.message || "Unable to load the latest results.";
        showToast(message, "danger");
      })
      .always(() => setLoading(false));
  }

  function bindUploadForm() {
    const form = $("#uploadForm");
    if (!form.length) {
      return;
    }

    const fileInput = form.find('input[name="dataset_file"]');
    const labelInput = form.find('input[name="label"]');
    const dropzone = $("#excelDropzone");

    if (dropzone.length) {
      dropzone.on("click", () => fileInput.trigger("click"));
    }

    fileInput.on("change", function () {
      if (this.files && this.files[0]) {
        if (dropzone.length) {
          dropzone.find(".dropzone-title").text(this.files[0].name);
          dropzone.addClass("dragover");
          setTimeout(() => dropzone.removeClass("dragover"), 450);
        }
      }
    });

    if (dropzone.length) {
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
    }

    form.on("submit", function (event) {
      event.preventDefault();
      const file = fileInput[0].files[0];
      if (!file) {
        showToast("Choose an Excel .xlsx file before uploading.", "danger");
        return;
      }
      if (!/(\.xlsx)$/i.test(file.name)) {
        showToast("Only Excel .xlsx files are supported.", "danger");
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
          }
        })
        .fail((xhr) => {
          const message = extractErrorMessage(xhr, "Upload failed.");
          showToast(message, "danger");
          alert(message);
        })
        .always(() => setLoading(false));
    });

    if (labelInput.length && dropzone.length) {
      labelInput.on("input", function () {
        dropzone.find(".dropzone-copy").text(this.value ? `Dataset label: ${this.value}` : "Or choose a file using the input above.");
      });
    }
  }

  function toggleStrategyFields() {
    const strategy = $("#strategy").val() || "ma";
    $(".strategy-field").hide();
    $(`.strategy-field[data-strategy="${strategy}"]`).show();

    let helpText = "";
    if (strategy === "ma") {
      helpText = "Buy when Short MA > Long MA. Sell when Short MA < Long MA.";
    } else if (strategy === "rsi") {
      helpText = "Buy when RSI < 30. Sell when RSI > 70.";
    } else if (strategy === "ema") {
      helpText = "Buy when Close > EMA. Sell when Close < EMA.";
    }
    $("#strategyHelp").text(helpText);
  }

  function bindBacktestForm() {
    const form = $("#strategyForm");
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
    $("#strategy").on("change", toggleStrategyFields);
    toggleStrategyFields();
    syncDatasetId();

    $("#runBacktestBtn").on("click", function () {
      const datasetId = syncDatasetId();
      if (!datasetId) {
        showToast("Upload a dataset before running the strategy.", "danger");
        return;
      }

      console.log("BUTTON CLICKED");

      setLoading(true);
      $.ajax({
        url: KINETIC.endpoints.runBacktest,
        type: "POST",
        data: {
          dataset_id: datasetId,
          strategy: $("#strategy").val(),
          short_window: form.find('input[name="short_window"]').val(),
          long_window: form.find('input[name="long_window"]').val(),
          rsi_period: form.find('input[name="rsi_period"]').val(),
          ema_window: form.find('input[name="ema_window"]').val(),
          csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
        },
      })
        .done((response) => {
          console.log("BACKTEST RESPONSE:", response);
          if (response.success) {
            alert("Backtest completed");
            showToast(response.message || "Backtest complete.", "success");
            updateSummary(
              response.total_profit || 0,
              response.num_trades || 0,
              response.win_percent || 0,
              response.initial_balance || 100000,
            );
            renderTrades(response.trades || []);

            if (document.getElementById("totalProfit")) {
              $("#totalProfit").text(response.total_profit ?? 0);
            }
            if (document.getElementById("numTrades")) {
              $("#numTrades").text(response.num_trades ?? 0);
            }
            if (document.getElementById("tradeTableBody")) {
              let rows = "";
              (response.trades || []).forEach((t) => {
                rows += `
                  <tr>
                    <td>${escapeHtml(t.entry_time ?? "-")}</td>
                    <td>${escapeHtml(t.exit_time ?? "-")}</td>
                    <td>${formatNumber(t.buy_price ?? 0, 2)}</td>
                    <td>${formatNumber(t.sell_price ?? 0, 2)}</td>
                    <td>${formatNumber(t.profit ?? 0, 2)}</td>
                  </tr>
                `;
              });
              $("#tradeTableBody").html(rows || '<tr><td colspan="5" class="text-center text-secondary py-4">No trades generated for the selected run.</td></tr>');
            }

            if (response.dataset) {
              refreshDatasetOptions(response.dataset);
            }
            KINETIC.latestResultId = String(response.result_id || "");
            $("body").attr("data-latest-result-id", KINETIC.latestResultId);

            if (KINETIC.pageSlug === "dashboard" && KINETIC.pages?.results && !document.getElementById("tradeTableBody") && !document.getElementById("tradeTable")) {
              window.location.href = KINETIC.pages.results;
            }
          }
        })
        .fail((xhr) => {
          console.log("ERROR:", xhr);
          const message = extractErrorMessage(xhr, "Backtest failed");
          showToast(message, "danger");
          alert("Backtest failed. Check console.");
        })
        .always(() => setLoading(false));
    });
  }

  function bindResultsPage() {
    if (!document.getElementById("tradeTable")) {
      return;
    }
    if (!window.KINETIC.latestResultId) {
      return;
    }
    loadLatestResult(window.KINETIC.latestResultId);
  }

  function bindDownloadTrades() {
    const downloadButton = $("#downloadTradeLog");
    if (!downloadButton.length) {
      return;
    }

    downloadButton.on("click", function () {
      const resultId = KINETIC.latestResultId || $("body").attr("data-latest-result-id") || "";
      if (!resultId) {
        showToast("Run a backtest before downloading the trade log.", "danger");
        return;
      }
      const query = resultId ? `?result_id=${encodeURIComponent(resultId)}` : "";
      window.location.href = `${KINETIC.endpoints.downloadTrades}${query}`;
    });
  }

  $(function () {
    console.log("JS LOADED");
    $.ajaxSetup({ headers: { "X-CSRFToken": getCookie("csrftoken") } });
    bindUploadForm();
    bindBacktestForm();
    bindResultsPage();
    bindDownloadTrades();
  });
})(jQuery);
