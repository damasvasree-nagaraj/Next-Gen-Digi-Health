fetch("/api/user")
  .then(res => {
    if (!res.ok) {
      window.location.href = "/";
    }
    return res.json();
  })
  .then(data => {
    document.getElementById("name").textContent = data.name;
    document.getElementById("email").textContent = data.email;
    document.getElementById("role").textContent = data.role;
  });
