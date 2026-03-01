// Get cart from localStorage
let cart = JSON.parse(localStorage.getItem("cart")) || {};

// DOM elements
const cartItemsDiv = document.getElementById("cartItems");
const totalAmountEl = document.getElementById("totalAmount");

// Render cart
function renderCart() {
  cartItemsDiv.innerHTML = "";
  let total = 0;

  const ids = Object.keys(cart);

  if (ids.length === 0) {
    cartItemsDiv.innerHTML = "<p>Your cart is empty</p>";
    totalAmountEl.innerText = "Total Amount: ₹0";
    return;
  }

  ids.forEach(id => {
    const item = cart[id];
    const itemTotal = item.price * item.qty;
    total += itemTotal;

    const div = document.createElement("div");
    div.className = "summary-item";
    div.innerHTML = `
      <span>${item.name} × ${item.qty}</span>
      <span>₹${itemTotal}</span>
    `;
    cartItemsDiv.appendChild(div);
  });

  totalAmountEl.innerText = `Total Amount: ₹${total}`;
}

// Go to checkout ONLY if cart has items
function goCheckout() {
  if (Object.keys(cart).length === 0) {
    alert("Your cart is empty!");
    return;
  }
  window.location.href = "/checkout";
}

// Initial render
renderCart();
