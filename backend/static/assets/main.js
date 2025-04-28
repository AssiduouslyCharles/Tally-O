// Wait until the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  // 1. Login button redirect
  const loginButton = document.getElementById("login-btn");
  if (loginButton) {
    loginButton.addEventListener("click", () => {
      // Redirect user to the OAuth login endpoint on your backend
      window.location.href = "/auth/ebay/login";
    });
  }

  // 3. Fetch and render sold items data
  fetch("/api/sold-items")
    .then((response) => response.json())
    .then((data) => {
      const tableBody = document.querySelector("#sold-items-table tbody");
      if (tableBody && Array.isArray(data)) {
        data.forEach((item) => {
          // 1. Format sold_date
          const soldDateFormatted = item.sold_date
            ? new Date(item.sold_date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })
            : "";

          const row = document.createElement("tr");
          row.dataset.orderId = item.order_id;
          row.dataset.finalFee = item.final_fee;
          row.dataset.fixedFinalFee = item.fixed_final_fee;
          row.dataset.internationalFee = item.international_fee;
          row.dataset.costToShip = item.cost_to_ship;
          row.dataset.shippingPaid = item.shipping_paid;
          row.dataset.netProfitMargin = item.net_profit_margin;
          row.dataset.soldForPrice = item.sold_for_price;

          row.innerHTML = `
          <td class="title-cell">${item.item_title ?? ""}</td>
          <td>${soldDateFormatted}</td>
          <td contenteditable="true" data-field="item_cost">
            ${item.item_cost != null ? "$" + item.item_cost : ""}
          </td>
          <td data-field="sold_for_price">
            ${item.sold_for_price != null ? "$" + item.sold_for_price : ""}
          </td>
          <td data-field="net_return">
            ${
              item.net_return != null
                ? "$" + parseFloat(item.net_return).toFixed(2)
                : ""
            }
          </td>
          <td data-field="roi">
            ${item.roi != null ? Math.round(item.roi) + "%" : ""}
          </td>
          <td data-field="net_profit_margin">
            ${
              item.net_profit_margin != null
                ? Math.round(item.net_profit_margin) + "%"
                : ""
            }
          </td>
          <td>
            ${item.time_to_sell != null ? item.time_to_sell + " Days" : ""}
          </td>
          <td contenteditable="true" data-field="purchased_at">
            ${item.purchased_at ?? ""}
          </td>
        `;
          tableBody.appendChild(row);
        });
        // 3. Attach blur event listeners to editable cells
        tableBody
          .querySelectorAll('td[contenteditable="true"]')
          .forEach((cell) => {
            cell.addEventListener("blur", async (e) => {
              console.log(
                "🟢 blur fired for",
                e.target.dataset.field,
                "order:",
                e.target.closest("tr").dataset.orderId
              );

              // Wrap the entire body in try/catch
              try {
                const td = e.target;
                const newValue = td.innerText.trim();
                const field = td.dataset.field;
                const row = td.closest("tr");
                const orderId = row.dataset.orderId;

                // Prepare payload
                const updates = {};

                if (field === "item_cost") {
                  // Parse values for recalculation
                  const soldFor = parseFloat(row.dataset.soldForPrice) || 0;
                  const shippingPaid =
                    parseFloat(row.dataset.shippingPaid) || 0;
                  const finalFee = parseFloat(row.dataset.finalFee) || 0;
                  const fixedFinalFee =
                    parseFloat(row.dataset.fixedFinalFee) || 0;
                  const international =
                    parseFloat(row.dataset.internationalFee) || 0;
                  const costToShip = parseFloat(row.dataset.costToShip) || 0;
                  const itemCost = parseFloat(newValue) || 0;

                  console.log({
                    soldFor,
                    shippingPaid,
                    finalFee,
                    fixedFinalFee,
                    international,
                    costToShip,
                    itemCost,
                  });
                  // Recalculate
                  const netReturn =
                    soldFor +
                    shippingPaid -
                    (finalFee +
                      fixedFinalFee +
                      international +
                      costToShip +
                      itemCost);
                  const roi = itemCost > 0 ? (netReturn / itemCost) * 100 : 0;
                  const netProfitMargin =
                    soldFor + shippingPaid > 0
                      ? (netReturn / (soldFor + shippingPaid)) * 100
                      : 0;

                  console.log({ netReturn, roi, netProfitMargin });

                  // Update UI
                  row.querySelector('td[data-field="net_return"]').innerText =
                    netReturn.toFixed(2);
                  row.querySelector('td[data-field="roi"]').innerText =
                    roi.toFixed(2);
                  row.querySelector(
                    'td[data-field="net_profit_margin"]'
                  ).innerText = netProfitMargin.toFixed(2);

                  // Build updates payload
                  updates.item_cost = itemCost;
                  updates.net_return = netReturn;
                  updates.roi = roi;
                  updates.net_profit_margin = netProfitMargin;
                } else {
                  updates[field] = newValue;
                }

                console.log(
                  "🔵 About to PATCH /api/sold-items/" + orderId,
                  updates
                );

                // Now this should definitely execute
                const res = await fetch(`/api/sold-items/${orderId}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(updates),
                });

                console.log("🔵 PATCH response status:", res.status);
                if (!res.ok) {
                  console.error("🔴 Update failed:", await res.text());
                }
              } catch (err) {
                console.error("🛑 Error in blur handler:", err);
              }
            });
          });
      }
    })
    .catch((error) => console.error("Error fetching sold items:", error));

  // 4. Fetch and render inventory items data
  fetch("/api/inventory-items")
    .then((response) => response.json())
    .then((data) => {
      const invBody = document.querySelector("#inventory-items-table tbody");
      if (invBody && Array.isArray(data)) {
        data.forEach((item) => {
          // 1) Compute "Listed For" as days since list_date
          let listedFor = "";
          if (item.list_date) {
            const dt = new Date(item.list_date);
            const diffMs = Date.now() - dt.getTime();
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            listedFor = diffDays + " Days";
          }

          // 2) Optional: format list_date as "April 22, 2025"
          const listDateFormatted = item.list_date
            ? new Date(item.list_date).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })
            : "";

          const row = document.createElement("tr");
          row.dataset.itemId = item.item_id;

          row.innerHTML = `
          <td>${item.item_title ?? ""}</td>
          <td>${listedFor}</td>
          <td contenteditable="true" data-field="storage_location">${
            item.storage_location ?? ""
          }</td>
          <td>${
            item.list_price != null
              ? "$" + parseFloat(item.list_price).toFixed(2)
              : ""
          }</td>
          <td contenteditable="true" data-field="item_cost">
            ${
              item.item_cost != null
                ? "$" + parseFloat(item.item_cost).toFixed(2)
                : ""
            }
          </td>
          <td contenteditable="true" data-field="purchased_at">
            ${item.purchased_at ?? ""}
          </td>
          <td>${listDateFormatted}</td>
          <td contenteditable="true" data-field="sku">${item.sku ?? ""}</td>
        `;
          invBody.appendChild(row);
        });

        // 5. Attach blur listeners for item_cost and purchased_at
        invBody
          .querySelectorAll('td[contenteditable="true"]')
          .forEach((cell) => {
            cell.addEventListener("blur", async (e) => {
              const td = e.target;
              const newValue = td.innerText.trim();
              const field = td.dataset.field; // "item_cost" or "purchased_at"
              const row = td.closest("tr");
              const itemId = row.dataset.itemId;

              const payload = {};
              if (field === "item_cost") {
                // strip non-numeric and parse
                const num = parseFloat(newValue.replace(/[^0-9.-]/g, "")) || 0;
                payload[field] = num;
              } else {
                payload[field] = newValue;
              }

              try {
                const res = await fetch(`/api/inventory-items/${itemId}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload),
                });
                if (!res.ok) {
                  console.error("Inventory update failed:", await res.text());
                }
              } catch (err) {
                console.error("Error updating inventory:", err);
              }
            });
          });
      }
    })
    .catch((err) => console.error("Error fetching inventory items:", err));

  // ────────────────────────────────────
  // Insights page: Google AreaChart
  // ────────────────────────────────────
  if (document.getElementById("insights-chart")) {
    // 1) Load the Google Charts corechart package
    google.charts.load("current", { packages: ["corechart"] });
    google.charts.setOnLoadCallback(initInsightsChart);

    function initInsightsChart() {
      const startInput = document.getElementById("insights-start");
      const endInput = document.getElementById("insights-end");
      const refreshBtn = document.getElementById("insights-refresh");

      // default to last 30 days
      const today = new Date().toISOString().slice(0, 10);
      const prior = new Date(Date.now() - 1000 * 60 * 60 * 24 * 30)
        .toISOString()
        .slice(0, 10);
      endInput.value = today;
      startInput.value = prior;

      refreshBtn.addEventListener("click", drawInsightsChart);
      drawInsightsChart();
    }

    async function drawInsightsChart() {
      const start = startInput.value;
      const end = endInput.value;
      const res = await fetch(
        `/api/insights-data?start_date=${start}&end_date=${end}`
      );
      const json = await res.json();
      const rows = json.data;
      const { total_gross, total_net, total_count, avg_npm } = json.summary;

      // 1) Update total gross & net
      document.getElementById("total-gross").textContent =
        "$" + total_gross.toFixed(2);
      document.getElementById("total-net").textContent =
        "$" + total_net.toFixed(2);

      // 2) Compute per‐sale averages and total NPM
      const avgGrossPerSale = total_count > 0 ? total_gross / total_count : 0;
      const avgNetPerSale = total_count > 0 ? total_net / total_count : 0;
      const totalNpm = total_gross > 0 ? (total_net / total_gross) * 100 : 0;

      // 3) Inject the four summary stats
      document.getElementById("avg-gross").textContent =
        "$" + avgGrossPerSale.toFixed(2);
      document.getElementById("avg-net").textContent =
        "$" + avgNetPerSale.toFixed(2);
      document.getElementById("npm").textContent = totalNpm.toFixed(1) + "%";
      document.getElementById("avg-npm").textContent = avg_npm.toFixed(1) + "%";

      // 4) Build the data array for the chart
      const dataArray = [
        ["Date", "Gross Sales", "Net Sales"],
        ...rows.map((r) => {
          const [y, m, d] = r.date
            .split("-")
            .map((v, i) => (i === 1 ? parseInt(v, 10) - 1 : parseInt(v, 10)));
          return [new Date(y, m, d), r.gross, r.net];
        }),
      ];

      const dataTable = google.visualization.arrayToDataTable(dataArray);

      // 5) Chart options (including any height/width you want)
      const options = {
        title: "Gross vs Net Sales Over Time",
        height: 300,
        hAxis: { title: "Date", format: "MMM d, yyyy" },
        vAxis: { title: "Amount (USD)", format: "currency" },
        isStacked: false,
        areaOpacity: 0.2,
        legend: { position: "top" },
      };

      // 6) Draw the chart
      const chartDiv = document.getElementById("insights-chart");
      const chart = new google.visualization.AreaChart(chartDiv);
      chart.draw(dataTable, options);
    }

    // keep it responsive
    window.addEventListener("resize", drawInsightsChart);
  }
});
