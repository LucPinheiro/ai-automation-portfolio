// Loaded on every page of a logged-in user: logout button and expired-session handling.
import { logout, setUnauthorizedHandler } from "./api.js";

function goToLogin(notice) {
  const next = window.location.pathname + window.location.search;
  window.location.assign(`/login?${new URLSearchParams({ notice, next })}`);
}

// Any API call answered with 401 not_authenticated (expired or closed session) leads to the login.
setUnauthorizedHandler(() => goToLogin("session_expired"));

document.getElementById("logout-button")?.addEventListener("click", async (event) => {
  // Guests are warned first: leaving deletes their generations.
  const warning = event.currentTarget.dataset.confirm;
  if (warning && !window.confirm(warning)) return;
  try {
    await logout();
  } catch {
    // Already logged out or the server is unreachable: the login page is still the right place.
  }
  window.location.assign("/login?notice=logged_out");
});
