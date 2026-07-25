const chatArea = document.getElementById('chat-area');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const chestButton = document.getElementById('chest-button');
const themeToggle = document.getElementById('theme-toggle');
const ttsToggle = document.getElementById('tts-toggle');
const assistantMsgTemplate = document.getElementById('assistant-msg-template');
const userMsgTemplate = document.getElementById('user-msg-template');
const micContainer = document.getElementById('mic-container');

let currentMicState = 'idle';

window.setMicState = function(state) {
  currentMicState = state;
  micContainer.classList.remove('listening', 'processing');
  if (state === 'listening') {
    micContainer.classList.add('listening');
  } else if (state === 'processing') {
    micContainer.classList.add('processing');
  }
};

// Set default theme from saved settings or default to light
async function loadSettings() {
  if (window.pywebview && window.pywebview.api) {
    const settings = await window.pywebview.api.load_settings();
    if (settings.theme === 'dark') {
      document.documentElement.dataset.theme = 'dark';
      themeToggle.textContent = '🌙';
    } else {
      document.documentElement.dataset.theme = 'light';
      themeToggle.textContent = '☀️';
    }
    if (settings.tts_muted) {
      ttsToggle.classList.add('muted');
    }
    
    // Load history
    const history = await window.pywebview.api.get_history();
    if (history) {
      history.forEach(msg => {
        if (msg.role === 'user') {
          appendUserMessage(msg.content);
        } else {
          appendAssistantMessage(msg.content);
        }
      });
    }
  }
}

window.addEventListener('pywebviewready', loadSettings);

themeToggle.addEventListener('click', async (e) => {
  e.stopPropagation();
  const currentTheme = document.documentElement.dataset.theme;
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = newTheme;
  themeToggle.textContent = newTheme === 'dark' ? '🌙' : '☀️';
  
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.save_theme(newTheme);
  }
});

ttsToggle.addEventListener('click', async () => {
  ttsToggle.classList.toggle('muted');
  const isMuted = ttsToggle.classList.contains('muted');
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.set_tts_muted(isMuted);
  }
});

function appendUserMessage(text) {
  const clone = userMsgTemplate.content.cloneNode(true);
  clone.querySelector('.bubble').textContent = text;
  chatArea.appendChild(clone);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function appendAssistantMessage(text) {
  const clone = assistantMsgTemplate.content.cloneNode(true);
  clone.querySelector('.bubble').textContent = text;
  chatArea.appendChild(clone);
  chatArea.scrollTop = chatArea.scrollHeight;
}

async function sendMessage(text) {
  appendUserMessage(text);
  chatInput.value = '';
  
  const typingBubble = showTypingIndicator();
  
  if (window.pywebview && window.pywebview.api) {
    chestButton.classList.add('listening');
    const response = await window.pywebview.api.send_message(text);
    chestButton.classList.remove('listening');
    
    // Clear mic processing state immediately if it was set, so it doesn't spin while typing
    if (currentMicState === 'processing') {
      setMicState('idle');
    }
    
    if (response) {
      await revealText(typingBubble, response);
    } else {
      // Remove the whole message container
      typingBubble.parentElement.remove();
    }
  } else {
    // Fallback for UI testing
    setTimeout(async () => {
      await revealText(typingBubble, "I am working offline right now.");
    }, 1000);
  }
}

function showTypingIndicator() {
  const clone = assistantMsgTemplate.content.cloneNode(true);
  const bubble = clone.querySelector('.bubble');
  
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  
  bubble.appendChild(indicator);
  chatArea.appendChild(clone);
  chatArea.scrollTop = chatArea.scrollHeight;
  
  return chatArea.lastElementChild.querySelector('.bubble');
}

function revealText(bubbleEl, fullText) {
  return new Promise(resolve => {
    bubbleEl.innerHTML = '';
    let i = 0;
    
    function typeNext() {
      if (i < fullText.length) {
        bubbleEl.textContent += fullText.charAt(i);
        i++;
        chatArea.scrollTop = chatArea.scrollHeight;
        
        const delay = Math.floor(Math.random() * 10) + 15;
        setTimeout(typeNext, delay);
      } else {
        resolve();
      }
    }
    
    typeNext();
  });
}

sendBtn.addEventListener('click', () => {
  const text = chatInput.value.trim();
  if (text) {
    sendMessage(text);
  }
});

chatInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    const text = chatInput.value.trim();
    if (text) {
      sendMessage(text);
    }
  }
});

// View Toggling
const navChat = document.getElementById('nav-chat');
const navMemory = document.getElementById('nav-memory');
const navHistory = document.getElementById('nav-history');
const navSettings = document.getElementById('nav-settings');
const chatView = document.getElementById('chat-view');
const memoryView = document.getElementById('memory-view');
const historyView = document.getElementById('history-view');
const settingsView = document.getElementById('settings-view');
const headerTitle = document.getElementById('header-title');

function switchView(viewName) {
  if (viewName === 'chat') {
    navChat.classList.add('active');
    navMemory.classList.remove('active');
    navHistory.classList.remove('active');
    if (navSettings) navSettings.classList.remove('active');
    chatView.style.display = 'flex';
    memoryView.style.display = 'none';
    historyView.style.display = 'none';
    if (settingsView) settingsView.style.display = 'none';
    headerTitle.textContent = 'Current Thread';
  } else if (viewName === 'memory') {
    navMemory.classList.add('active');
    navChat.classList.remove('active');
    navHistory.classList.remove('active');
    if (navSettings) navSettings.classList.remove('active');
    memoryView.style.display = 'flex';
    chatView.style.display = 'none';
    historyView.style.display = 'none';
    if (settingsView) settingsView.style.display = 'none';
    headerTitle.textContent = 'Memory';
    loadMemoryData();
  } else if (viewName === 'history') {
    navHistory.classList.add('active');
    navChat.classList.remove('active');
    navMemory.classList.remove('active');
    if (navSettings) navSettings.classList.remove('active');
    historyView.style.display = 'flex';
    chatView.style.display = 'none';
    memoryView.style.display = 'none';
    if (settingsView) settingsView.style.display = 'none';
    headerTitle.textContent = 'History';
    loadHistoryData();
  } else if (viewName === 'settings') {
    if (navSettings) navSettings.classList.add('active');
    navChat.classList.remove('active');
    navMemory.classList.remove('active');
    navHistory.classList.remove('active');
    if (settingsView) settingsView.style.display = 'flex';
    chatView.style.display = 'none';
    memoryView.style.display = 'none';
    historyView.style.display = 'none';
    headerTitle.textContent = 'Settings & Diagnostics';
  }
}

navChat.addEventListener('click', () => switchView('chat'));
navMemory.addEventListener('click', () => switchView('memory'));
navHistory.addEventListener('click', () => switchView('history'));
if (navSettings) navSettings.addEventListener('click', () => switchView('settings'));

// Test Connection Button in Settings
const testConnectionBtn = document.getElementById('test-connection-btn');
const apiStatusList = document.getElementById('api-status-list');

if (testConnectionBtn) {
  testConnectionBtn.addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    
    testConnectionBtn.disabled = true;
    testConnectionBtn.textContent = 'Testing...';
    apiStatusList.innerHTML = '<div class="fact-row"><span class="fact-value" style="color: var(--text-secondary);">Testing API connections, please wait...</span></div>';
    
    try {
      const results = await window.pywebview.api.test_api_keys();
      apiStatusList.innerHTML = '';
      
      results.forEach(res => {
        const row = document.createElement('div');
        row.className = 'fact-row';
        row.innerHTML = `
          <div class="fact-content">
            <div class="fact-key">${res.icon} ${res.provider}: ${res.status}</div>
            <div class="fact-value" style="margin-top: 4px; color: ${res.success ? 'var(--text-primary)' : (res.status === 'Not configured' ? 'var(--text-secondary)' : '#e53935')}">${res.detail}</div>
          </div>
        `;
        apiStatusList.appendChild(row);
      });
    } catch (e) {
      apiStatusList.innerHTML = `<div class="fact-row"><span class="fact-value" style="color: #e53935;">Error running diagnostics: ${e}</span></div>`;
    } finally {
      testConnectionBtn.disabled = false;
      testConnectionBtn.textContent = 'Test Connection';
    }
  });
}

// Memory Data Loading
const factsList = document.getElementById('facts-list');
const historyList = document.getElementById('history-list');

async function loadMemoryData() {
  if (!window.pywebview || !window.pywebview.api) return;
  
  // Load Facts
  factsList.innerHTML = '<div style="color: var(--text-secondary)">Loading...</div>';
  const facts = await window.pywebview.api.get_facts();
  factsList.innerHTML = '';
  
  if (Object.keys(facts).length === 0) {
    factsList.innerHTML = '<div class="fact-row"><span class="fact-value">No facts learned yet — Sara will remember things as you chat.</span></div>';
  } else {
    for (const [key, value] of Object.entries(facts)) {
      const row = document.createElement('div');
      row.className = 'fact-row';
      row.innerHTML = `
        <div class="fact-content">
          <div class="fact-key">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
          <div class="fact-value">${value}</div>
        </div>
        <button class="delete-btn" title="Delete Fact">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      `;
      row.querySelector('.delete-btn').addEventListener('click', async () => {
        await window.pywebview.api.delete_fact(key);
        loadMemoryData(); // reload
      });
      factsList.appendChild(row);
    }
  }
}

async function loadHistoryData() {
  if (!window.pywebview || !window.pywebview.api) return;
  
  // Load History
  historyList.innerHTML = '<div style="color: var(--text-secondary)">Loading...</div>';
  const sessions = await window.pywebview.api.get_history_list();
  historyList.innerHTML = '';
  
  if (sessions.length === 0) {
    historyList.innerHTML = '<div class="session-group"><div class="session-header" style="cursor:default">No history found.</div></div>';
  } else {
    sessions.forEach((session, index) => {
      // Format date
      const date = new Date(session.latest_timestamp + "Z"); // Add Z to specify UTC if DB is UTC
      const dateStr = isNaN(date.getTime()) ? session.latest_timestamp : date.toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
      });
      
      const group = document.createElement('div');
      group.className = 'session-group';
      if (index === 0) group.classList.add('expanded'); // Expand first one by default
      
      const header = document.createElement('div');
      header.className = 'session-header';
      header.innerHTML = `<span>Session &mdash; ${dateStr}</span><span>▼</span>`;
      
      header.addEventListener('click', () => {
        group.classList.toggle('expanded');
      });
      
      const messagesContainer = document.createElement('div');
      messagesContainer.className = 'session-messages';
      
      session.messages.forEach(msg => {
        const row = document.createElement('div');
        row.className = 'history-row';
        row.innerHTML = `
          <div class="history-role" style="color: ${msg.role === 'user' ? 'var(--text-primary)' : 'var(--accent)'}">${msg.role}</div>
          <div class="history-msg">${msg.content}</div>
        `;
        messagesContainer.appendChild(row);
      });
      
      group.appendChild(header);
      group.appendChild(messagesContainer);
      historyList.appendChild(group);
    });
  }
}

document.getElementById('new-session-btn').addEventListener('click', async () => {
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.new_session();
    chatArea.innerHTML = '';
    loadMemoryData();
  }
});

document.getElementById('clear-history-btn').addEventListener('click', async () => {
  if (confirm("Are you sure you want to clear ALL conversation history? (Learned facts will be kept)")) {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.clear_history();
      chatArea.innerHTML = '';
      loadHistoryData();
    }
  }
});

micBtn.addEventListener('click', async () => {
  if (currentMicState === 'listening') {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.stop_listening();
    }
    setMicState('processing');
    return;
  }

  if (currentMicState === 'idle') {
    if (window.pywebview && window.pywebview.api) {
      setMicState('listening');
      const text = await window.pywebview.api.start_listening();
      if (text) {
        setMicState('processing');
        await sendMessage(text);
      }
      setMicState('idle');
    }
  }
});

// Memory Consent Toast Logic
let pendingFacts = null;

window.showMemoryConsentToast = function(b64_facts) {
  try {
    const jsonStr = atob(b64_facts);
    pendingFacts = JSON.parse(jsonStr);
    
    const factsHtml = Object.entries(pendingFacts)
      .map(([k, v]) => `<div><b>${k}</b>: ${v}</div>`)
      .join('');
      
    document.getElementById('toast-facts').innerHTML = factsHtml;
    document.getElementById('memory-toast').classList.add('show');
  } catch(e) {
    console.error("Failed to parse facts", e);
  }
};

document.getElementById('toast-yes-btn').addEventListener('click', async () => {
  document.getElementById('memory-toast').classList.remove('show');
  if (window.pywebview && window.pywebview.api && pendingFacts) {
    await window.pywebview.api.set_memory_enabled(true, pendingFacts);
    pendingFacts = null;
    loadMemoryData(); // refresh if we're on the memory tab
  }
});

document.getElementById('toast-no-btn').addEventListener('click', async () => {
  document.getElementById('memory-toast').classList.remove('show');
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.set_memory_enabled(false);
    pendingFacts = null;
  }
});

// Sidebar New Chat Button
const sidebarNewChatBtn = document.getElementById('sidebar-new-chat-btn');

function updateNewChatBtnState() {
  const userMessages = chatArea.querySelectorAll('.message.user');
  if (userMessages.length === 0) {
    sidebarNewChatBtn.disabled = true;
    sidebarNewChatBtn.style.opacity = '0.5';
    sidebarNewChatBtn.style.cursor = 'not-allowed';
  } else {
    sidebarNewChatBtn.disabled = false;
    sidebarNewChatBtn.style.opacity = '1';
    sidebarNewChatBtn.style.cursor = 'pointer';
  }
}

// Observe chatArea changes to update the button state
const observer = new MutationObserver(updateNewChatBtnState);
observer.observe(chatArea, { childList: true });
// initial state
updateNewChatBtnState();

sidebarNewChatBtn.addEventListener('click', async () => {
  if (sidebarNewChatBtn.disabled) return;
  if (window.pywebview && window.pywebview.api) {
    await window.pywebview.api.new_session();
    chatArea.innerHTML = '';
    chatInput.value = '';
    // Show fresh greeting
    const typingBubble = showTypingIndicator();
    await revealText(typingBubble, "Hi, I'm Sara. How can I help you today?");
    // Make sure we are on the chat view
    switchView('chat');
  }
});
