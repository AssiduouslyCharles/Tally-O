// frontend/assets/main.js

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
          const row = document.createElement("tr");
          row.dataset.orderId = item.order_id; // Store order ID in the row for future reference
          row.innerHTML = `
                <td>${item.item_title}</td>
                <td>${item.sold_date}</td>
                <td contenteditable="true" data-field="item_cost">${item.item_cost}</td>
                <td>${item.sold_for_price}</td>
                <td>${item.net_profit_margin}</td>
                <td>${item.roi}</td>
                <td>${item.time_to_sell}</td>
                <td contenteditable="true" data-field="purchased_at">${item.purchased_at}</td>
              `;
          tableBody.appendChild(row);
        });
        // 3. Attach blur event listeners to editable cells
        tableBody
          .querySelectorAll('td[contenteditable="true"]')
          .forEach((cell) => {
            cell.addEventListener("blur", async (e) => {
              const td = e.target;
              const newValue = td.innerText.trim();
              const field = td.dataset.field;
              const orderId = td.closest("tr").dataset.orderId;

              try {
                const res = await fetch(`/api/sold-items/${orderId}`, {
                  method: "PATCH",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({ [field]: newValue }),
                });
                if (!res.ok) {
                  console.error("Update failed:", await res.text());
                }
              } catch (err) {
                console.error("Error updating field:", err);
              }
            });
          });
      }
    })
    .catch((error) => console.error("Error fetching sold items:", error));
});
