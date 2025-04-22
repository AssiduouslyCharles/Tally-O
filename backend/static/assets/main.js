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

  // 2. Fetch and render transactions data
  fetch("/api/transactions")
    .then((response) => response.json())
    .then((data) => {
      const tableBody = document.querySelector("#transactions-table tbody");
      if (tableBody && Array.isArray(data)) {
        data.forEach((txn) => {
          const row = document.createElement("tr");
          row.innerHTML = `
                <td>${txn.order_id}</td>
                <td>${txn.line_item_id}</td>
                <td>${txn.transaction_type}</td>
                <td>${txn.transaction_date}</td>
                <td>${txn.amount_value}</td>
              `;
          tableBody.appendChild(row);
        });
      }
    })
    .catch((error) => console.error("Error fetching transactions:", error));

  // 3. Fetch and render sold items data
  fetch("/api/sold-items")
    .then((response) => response.json())
    .then((data) => {
      const tableBody = document.querySelector("#sold-items-table tbody");
      if (tableBody && Array.isArray(data)) {
        data.forEach((item) => {
          const row = document.createElement("tr");
          row.innerHTML = `
                <td>${item.order_id}</td>
                <td>${item.item_title}</td>
                <td>${item.sold_date}</td>
                <td>${item.sold_for_price}</td>
              `;
          tableBody.appendChild(row);
        });
      }
    })
    .catch((error) => console.error("Error fetching sold items:", error));
});
