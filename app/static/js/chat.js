// S3 - sends chat questions to /assistant/ask and shows the answer.
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sendButton = document.getElementById("chat-send");
const log = document.getElementById("chat-log");
const loading = document.getElementById("chat-loading");

function addMessage(kind, text) {
  document.getElementById("chat-empty")?.remove();
  const div = document.createElement("div");
  div.className = `chat-msg chat-${kind}`;
  div.textContent = text; // textContent, never innerHTML: AI output is not trusted
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function setLoading(isLoading) {
  loading.hidden = !isLoading;
  input.disabled = isLoading;
  sendButton.disabled = isLoading;
}

async function ask(question) {
  addMessage("user", question);
  setLoading(true);
  try {
    const response = await fetch(form.action, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": form.dataset.csrf },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    addMessage(data.ok ? "assistant" : "error", data.ok ? data.message.content : data.error);
  } catch {
    addMessage("error", "Connection problem. Please try again.");
  } finally {
    setLoading(false);
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

document.querySelectorAll(".chat-example").forEach((button) => {
  button.addEventListener("click", () => ask(button.textContent.trim()));
});

log.scrollTop = log.scrollHeight;
