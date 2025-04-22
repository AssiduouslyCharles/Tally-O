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
          row.innerHTML = `
                <td>${item.item_title}</td>
                <td>${item.sold_date}</td>
                <td>${item.item_cost}</td>
                <td>${item.sold_for_price}</td>
                <td>${item.net_profit_margin}</td>
                <td>${item.roi}</td>
                <td>${item.time_to_sell}</td>
                <td>${item.purchased_at}</td>
              `;
          tableBody.appendChild(row);
        });
      }
    })
    .catch((error) => console.error("Error fetching sold items:", error));
});
