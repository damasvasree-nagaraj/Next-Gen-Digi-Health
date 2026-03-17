const chatMessages = document.getElementById("chatMessages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const languageSelect = document.getElementById("languageSelect");
const voiceBtn = document.getElementById("voiceBtn");

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

/* ================= TEXT TO SPEECH ================= */

function speakResponse(text) {

  const selectedLang = document.getElementById("languageSelect").value;

  const utterance = new SpeechSynthesisUtterance(text);

  // Map languages correctly
  const langMap = {
    "en": "en-US",
    "ta": "ta-IN",
    "hi": "hi-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "pa": "pa-IN"
  };

  utterance.lang = langMap[selectedLang] || "en-US";

  const voices = speechSynthesis.getVoices();

  // Try to find correct language voice
  const voice = voices.find(v => v.lang === utterance.lang);

  if (voice) {
    utterance.voice = voice;
  }

  speechSynthesis.speak(utterance);
}
/* ================= SEND MESSAGE ================= */

function sendMessage(text) {

  if (!text) return;

  addMessage(text, "user");
  saveMessage(text, "user");

  showTyping();

  const lang = languageSelect.value || "en";

  fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: text,
      language: lang
    })
  })
    .then(res => res.json())
    .then(data => {

      setTimeout(() => {

        removeTyping();

        addMessage(data.reply, "bot");
        saveMessage(data.reply, "bot");
        speakResponse(data.reply);

      }, 600);

    });
}

/* ================= SEND BUTTON ================= */

sendBtn.onclick = () => {

  const text = userInput.value.trim();

  userInput.value = "";

  sendMessage(text);

};

/* ================= ENTER KEY SEND ================= */

userInput.addEventListener("keypress", function(e){

  if(e.key === "Enter"){

    const text = userInput.value.trim();

    userInput.value = "";

    sendMessage(text);

  }

});

/* ================= QUICK QUESTIONS ================= */

document.querySelectorAll(".quick-questions button").forEach(btn => {

  btn.onclick = () => {

    const q = btn.textContent.trim();

    sendMessage(q);

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

/* ================= VOICE INPUT ================= */

/* ================= VOICE INPUT ================= */

if ("webkitSpeechRecognition" in window) {

  const recognition = new webkitSpeechRecognition();

  recognition.continuous = false;
  recognition.interimResults = false;

  voiceBtn.onclick = () => {

    const lang = languageSelect.value || "en-US";

    recognition.lang = lang;

    recognition.start();

  };

  recognition.onresult = function(event){

    const speech = event.results[0][0].transcript;

    userInput.value = speech;

    sendMessage(speech);

  };

}