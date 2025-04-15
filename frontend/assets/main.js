// Wait until the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  const loginButton = document.getElementById("login-btn");

  // Attach a click event to the login button
  loginButton.addEventListener("click", () => {
    // Redirect user to the OAuth login endpoint provided by your Flask backend.
    // Replace the URL below with your actual endpoint if it differs.
    window.location.href = "http://127.0.0.1:5000/auth/ebay/login";
  });
});
