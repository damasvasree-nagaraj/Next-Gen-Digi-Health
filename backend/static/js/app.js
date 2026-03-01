function login() {
  fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.getElementById("email").value,
      password: document.getElementById("password").value
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      alert(data.error || "Login failed");
    }
  })
  .catch(err => {
    alert("Server error");
    console.error(err);
  });
}

function register() {
  fetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.getElementById("name").value,
      email: document.getElementById("email").value,
      password: document.getElementById("password").value,
      role: document.getElementById("role").value
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      alert(data.error || "Registration failed");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".feature-card").forEach(card => {
    const bg = card.getAttribute("data-bg");
    if (bg) {
      card.style.backgroundImage = `url('${bg}')`;
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".feature-card");
  if (!cards.length) return;

  cards.forEach(card => {
    const bg = card.dataset.bg;
    card.style.backgroundImage = `url('${bg}')`;
  });
});
