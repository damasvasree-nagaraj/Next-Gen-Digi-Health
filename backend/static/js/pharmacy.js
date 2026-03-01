const medicines = [
  { id: 1, name: "Paracetamol 500mg", price: 49, category: "Tablets" },
  { id: 2, name: "Azithromycin 500mg", price: 129, category: "Tablets" },
  { id: 3, name: "Cetirizine 10mg", price: 39, category: "Tablets" },
  { id: 4, name: "Dolo 650", price: 32, category: "Tablets" },
  { id: 5, name: "Amoxicillin 500mg", price: 89, category: "Tablets" },
  { id: 6, name: "Metformin 500mg", price: 79, category: "Tablets" },
  { id: 7, name: "Vitamin C Tablets", price: 59, category: "Tablets" },
  { id: 8, name: "Calcium + D3", price: 149, category: "Tablets" },
  { id: 9, name: "Ibuprofen 400mg", price: 69, category: "Tablets" },
  { id: 10, name: "Pantoprazole 40mg", price: 95, category: "Tablets" },

  { id: 11, name: "Cough Syrup", price: 99, category: "Syrups" },
  { id: 12, name: "Digene Syrup", price: 110, category: "Syrups" },
  { id: 13, name: "ORS Liquid", price: 45, category: "Syrups" },
  { id: 14, name: "Iron Tonic", price: 125, category: "Syrups" },
  { id: 15, name: "Vitamin B-Complex Syrup", price: 135, category: "Syrups" },

  { id: 16, name: "Insulin Injection", price: 599, category: "Devices" },
  { id: 17, name: "Digital Thermometer", price: 250, category: "Devices" },
  { id: 18, name: "BP Monitor", price: 1299, category: "Devices" },
  { id: 19, name: "Glucometer", price: 1599, category: "Devices" },
  { id: 20, name: "Nebulizer Machine", price: 1899, category: "Devices" },
  { id: 21, name: "Pulse Oximeter", price: 999, category: "Devices" },
  { id: 22, name: "Hot Water Bag", price: 299, category: "Devices" },
  { id: 23, name: "Hand Sanitizer", price: 75, category: "Devices" },
  { id: 24, name: "Face Mask (Pack of 10)", price: 120, category: "Devices" },
  { id: 25, name: "Pain Relief Spray", price: 180, category: "Devices" }
];

function getCart() {
  return JSON.parse(localStorage.getItem("cart")) || [];
}

function saveCart(cart) {
  localStorage.setItem("cart", JSON.stringify(cart));
}

function renderMedicines(list) {
  const grid = document.getElementById("medicineGrid");
  const cart = getCart();
  grid.innerHTML = "";

  list.forEach(med => {
    const item = cart.find(i => i.id === med.id);
    const qty = item ? item.qty : 0;

    grid.innerHTML += `
      <div class="medicine-card">
        <h3>${med.name}</h3>
        <p class="price">₹${med.price}</p>
        <div class="qty-control">
          <button onclick="updateQty(${med.id}, -1)">−</button>
          <span id="qty-${med.id}">${qty}</span>
          <button onclick="updateQty(${med.id}, 1)">+</button>
        </div>
      </div>
    `;
  });
}

function applyFilters() {
  const searchText = document.getElementById("searchInput").value.toLowerCase();
  const category = document.getElementById("categoryFilter").value;

  const filtered = medicines.filter(m =>
    m.name.toLowerCase().includes(searchText) &&
    (category === "All" || m.category === category)
  );

  renderMedicines(filtered);
}

function updateQty(id, change) {
  let cart = getCart();
  const med = medicines.find(m => m.id === id);
  let item = cart.find(i => i.id === id);

  if (!item && change > 0) {
    cart.push({ id, name: med.name, price: med.price, qty: 1 });
  } else if (item) {
    item.qty += change;
    if (item.qty <= 0) {
      cart = cart.filter(i => i.id !== id);
    }
  }

  saveCart(cart);
  renderMedicines(medicines);
}

// Initial load
renderMedicines(medicines);
