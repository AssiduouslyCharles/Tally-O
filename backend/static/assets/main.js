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
          <td>${item.item_title ?? ""}</td>
          <td>${soldDateFormatted}</td>
          <td contenteditable="true" data-field="item_cost">
            ${item.item_cost != null ? "$" + item.item_cost : ""}
          </td>
          <td data-field="sold_for_price">
            ${item.sold_for_price != null ? "$" + item.sold_for_price : ""}
          </td>
          <td data-field="net_return">
            ${item.net_return != null ? "$" + item.net_return : ""}
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
});
