const chatMessages = document.getElementById("chatMessages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

/* ================= CHAT HISTORY ================= */
let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

chatHistory.forEach(msg => {
  addMessage(msg.text, msg.type);
});

/* ================= CORE FUNCTIONS ================= */

function addMessage(text, type) {
  const div = document.createElement("div");
  div.className = type === "user" ? "user-message fade-in" : "bot-message fade-in";
  div.textContent = text;
  chatMessages.appendChild(div);
  smoothScroll();
}

function saveMessage(text, type) {
  chatHistory.push({ text, type });
  localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

function smoothScroll() {
  chatMessages.scrollTo({
    top: chatMessages.scrollHeight,
    behavior: "smooth"
  });
}

/* ================= TYPING INDICATOR ================= */

function showTyping() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "bot-message typing-indicator";
  typingDiv.id = "typingIndicator";
  typingDiv.innerHTML = `
    <div class="typing-text">
      AI is thinking
      <span class="typing">
        <span></span><span></span><span></span>
      </span>
    </div>
  `;
  chatMessages.appendChild(typingDiv);
  smoothScroll();
}

function removeTyping() {
  const typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();
}

/* ================= SEND MESSAGE ================= */

function sendMessage(text) {
  if (!text) return;

  addMessage(text, "user");
  saveMessage(text, "user");

  showTyping();

  fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text })
  })
    .then(res => res.json())
    .then(data => {
      setTimeout(() => {
        removeTyping();
        addMessage(data.reply, "bot");
        saveMessage(data.reply, "bot");
      }, 600);
    });
}

sendBtn.onclick = () => {
  const text = userInput.value.trim();
  userInput.value = "";
  sendMessage(text);
};

/* ================= QUICK QUESTIONS (FIXED) ================= */

document.querySelectorAll(".quick-questions button").forEach(btn => {
  btn.onclick = () => {
    const q = btn.textContent.trim();
    sendMessage(q);   // ✅ SAME FLOW AS NORMAL CHAT
  };
});

/* ================= NEW CHAT ================= */

document.querySelector(".new-chat-btn").onclick = () => {
  chatMessages.innerHTML = `
    <div class="bot-message">
      👋 Hello! I’m your AI Health Assistant. How can I help you today?
    </div>
  `;
  chatHistory = [];
  localStorage.removeItem("chatHistory");
};
