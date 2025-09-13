// Guesty AI Chat Application
class GuestyChat {
    constructor() {
        this.sessions = [];
        this.currentSession = null;
        this.messages = [];
        this.isLoading = false;
        this.sidebarCollapsed = false;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSessions();
        this.scrollToBottom();
    }

    bindEvents() {
        // New chat button
        document.getElementById('new-chat-btn').addEventListener('click', () => {
            this.createNewSession();
        });

        // Sidebar toggle
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            this.toggleSidebar();
        });

        // Message form submission
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSendMessage();
        });

        // Message input enter key
        document.getElementById('message-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        // Auto-resize textarea
        document.getElementById('message-input').addEventListener('input', (e) => {
            this.autoResizeTextarea(e.target);
        });

        // Suggestion buttons
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const suggestion = btn.textContent.trim();
                this.sendMessage(suggestion);
            });
        });
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        const sidebar = document.getElementById('sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle');
        
        if (this.sidebarCollapsed) {
            sidebar.classList.add('collapsed');
            toggleBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>';
        } else {
            sidebar.classList.remove('collapsed');
            toggleBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>';
        }
    }

    async loadSessions() {
        try {
            const response = await fetch('/api/sessions/');
            const data = await response.json();
            
            if (response.ok) {
                this.sessions = data.sessions;
                this.renderSessions();
                
                if (this.sessions.length > 0 && !this.currentSession) {
                    this.selectSession(this.sessions[0]);
                }
            } else {
                console.error('Error loading sessions:', data.error);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    generateGuestySessionId() {
        // Generate 16 random alphanumeric characters
        const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
        let result = '';
        for (let i = 0; i < 16; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return `guesty-${result}`;
    }

    isSessionIdUnique(sessionId) {
        return !this.sessions.some(session => session.guesty_session_id === sessionId);
    }

    generateUniqueGuestySessionId() {
        let sessionId = this.generateGuestySessionId();
        let attempts = 0;
        
        // Ensure uniqueness, add timestamp if needed
        while (!this.isSessionIdUnique(sessionId) && attempts < 10) {
            const timestamp = Date.now().toString().slice(-4);
            sessionId = `guesty-${this.generateGuestySessionId().split('-')[1].slice(0, 12)}${timestamp}`;
            attempts++;
        }
        
        return sessionId;
    }

    async createNewSession() {
        const internalId = `gs_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const guestySessionId = this.generateUniqueGuestySessionId();
        
        const newSession = {
            id: internalId,
            session_id: internalId,
            guesty_session_id: guestySessionId,
            title: "New Chat",
            message_count: 0,
            last_message: "",
            created_date: new Date().toISOString()
        };

        try {
            const response = await fetch('/api/sessions/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newSession)
            });

            const data = await response.json();
            
            if (response.ok) {
                this.sessions.unshift(data);
                this.renderSessions();
                this.selectSession(data);
            } else {
                console.error('Error creating session:', data.error);
            }
        } catch (error) {
            console.error('Error creating session:', error);
        }
    }

    selectSession(session) {
        this.currentSession = session;
        this.loadMessages(session.id);
        this.renderSessions();
        this.hideWelcomeScreen();
    }

    async loadMessages(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}/messages/`);
            const data = await response.json();
            
            if (response.ok) {
                this.messages = data.messages;
                this.renderMessages();
                this.scrollToBottom();
            } else {
                console.error('Error loading messages:', data.error);
                this.messages = [];
                this.renderMessages();
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.messages = [];
            this.renderMessages();
        }
    }

    async handleSendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || this.isLoading) return;

        input.value = '';
        this.autoResizeTextarea(input);

        // Create session if none exists
        if (!this.currentSession) {
            await this.createNewSession();
        }

        await this.sendMessage(message);
    }

    async sendMessage(content) {
        if (!this.currentSession) {
            await this.createNewSession();
        }

        try {
            // Add user message to UI immediately
            const userMessage = {
                id: Date.now(),
                session_id: this.currentSession.id,
                content: content,
                role: "user",
                timestamp: new Date().toISOString()
            };

            this.messages.push(userMessage);
            this.renderMessages();
            this.scrollToBottom();
            this.hideWelcomeScreen();

            // Show loading
            this.isLoading = true;
            this.showLoading();

            // Send message to API
            const response = await fetch('/api/messages/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.currentSession.id,
                    content: content
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Update user message with server response
                const userMsgIndex = this.messages.findIndex(m => m.id === userMessage.id);
                if (userMsgIndex !== -1) {
                    this.messages[userMsgIndex] = data.user_message;
                }
                
                // Add AI message
                this.messages.push(data.ai_message);
                this.hideLoading();
                this.renderMessages();
                this.scrollToBottom();

                // Reload sessions to get updated metadata
                await this.loadSessions();
            } else {
                console.error('Error sending message:', data.error);
                this.hideLoading();
                // Remove the optimistic user message
                this.messages = this.messages.filter(m => m.id !== userMessage.id);
                this.renderMessages();
                alert('Error sending message. Please try again.');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideLoading();
            alert('Error sending message. Please try again.');
        } finally {
            this.isLoading = false;
        }
    }

    renderSessions() {
        const sessionsList = document.getElementById('sessions-list');
        sessionsList.innerHTML = '';

        this.sessions.forEach(session => {
            const sessionElement = document.createElement('button');
            sessionElement.className = `session-item w-full justify-start text-left p-3 rounded-lg transition-colors ${
                this.currentSession?.id === session.id 
                    ? 'bg-slate-700 text-white' 
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`;
            
            // Handle old sessions without guesty_session_id
            const displaySessionId = session.guesty_session_id || null;
            const fallbackTitle = session.guesty_session_id 
                ? `Chat ${session.guesty_session_id.slice(-4)}` 
                : `Chat ${session.session_id.slice(-4)}`;
            
            sessionElement.innerHTML = `
                <div class="flex items-start gap-3 w-full group">
                    <svg class="w-4 h-4 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                    </svg>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between mb-1">
                            <p class="text-sm font-medium truncate">
                                ${session.title || fallbackTitle}
                            </p>
                            <div class="flex items-center gap-1">
                                ${displaySessionId ? `
                                    <span class="text-xs px-2 py-1 bg-emerald-600 text-white rounded-full font-mono text-[10px] flex-shrink-0 sidebar-text">
                                        ${displaySessionId.slice(-8)}
                                    </span>
                                ` : `
                                    <button class="assign-session-id-btn text-xs px-2 py-1 bg-slate-600 hover:bg-slate-500 text-white rounded-full text-[10px] flex-shrink-0 sidebar-text opacity-0 group-hover:opacity-100 transition-opacity" data-session-id="${session.id}">
                                        Assign ID
                                    </button>
                                `}
                                <button class="delete-session-btn text-slate-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-1" data-session-id="${session.id}">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        ${displaySessionId && !this.sidebarCollapsed ? `
                            <p class="text-xs text-slate-500 font-mono mb-1 sidebar-text truncate">
                                ${displaySessionId}
                            </p>
                        ` : ''}
                        <p class="text-xs text-slate-400 truncate sidebar-text">
                            ${session.last_message || "No messages yet"}
                        </p>
                    </div>
                </div>
            `;
            
            sessionElement.addEventListener('click', (e) => {
                // Don't select session if clicking on action buttons
                if (e.target.closest('.delete-session-btn') || e.target.closest('.assign-session-id-btn')) {
                    return;
                }
                this.selectSession(session);
            });

            // Add event listeners for action buttons
            const deleteBtn = sessionElement.querySelector('.delete-session-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm('Are you sure you want to delete this chat session?')) {
                        this.deleteSession(session.id);
                    }
                });
            }

            const assignBtn = sessionElement.querySelector('.assign-session-id-btn');
            if (assignBtn) {
                assignBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.assignGuestySessionId(session);
                });
            }
            
            sessionsList.appendChild(sessionElement);
        });
    }

    renderMessages() {
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';

        this.messages.forEach((message, index) => {
            const messageElement = this.createMessageElement(message, index === this.messages.length - 1);
            messagesContainer.appendChild(messageElement);
        });
    }

    createMessageElement(message, isLast) {
        const isUser = message.role === 'user';
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble flex gap-4 p-4 ${isUser ? 'justify-end' : 'justify-start'}`;
        
        const timestamp = message.timestamp ? new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
        const messageId = message.id || `msg-${Date.now()}`;
        
        messageDiv.innerHTML = `
            ${!isUser ? `
                <div class="w-8 h-8 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center flex-shrink-0">
                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                    </svg>
                </div>
            ` : ''}
            
            <div class="max-w-[80%] ${isUser ? 'order-first' : ''}">
                <div class="rounded-2xl px-4 py-3 ${
                    isUser
                        ? 'bg-emerald-600 text-white ml-auto'
                        : 'bg-slate-100 text-slate-900 border border-slate-200'
                }">
                    <p class="mb-0 ${isUser ? 'text-white' : 'text-slate-900'}">${this.formatMessage(message.content)}</p>
                    ${!isUser && message.sql_query ? `
                        <button class="sql-toggle-btn mt-2 flex items-center gap-1 text-xs ${message.query_status === 'error' ? 'text-red-600' : 'text-emerald-600'} hover:opacity-80 transition-opacity" data-message-id="${messageId}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                            </svg>
                            <span>View SQL Query</span>
                        </button>
                        <div id="sql-${messageId}" class="sql-query-container hidden mt-3 p-3 bg-slate-900 rounded-lg overflow-x-auto">
                            <pre class="text-xs text-slate-100 whitespace-pre-wrap font-mono">${this.escapeHtml(message.sql_query)}</pre>
                        </div>
                    ` : ''}
                </div>
                <div class="text-xs text-slate-400 mt-1 ${isUser ? 'text-right' : 'text-left'}">
                    ${timestamp}
                    ${!isUser && message.query_status === 'error' ? '<span class="text-red-500 ml-2">⚠️ Query Error</span>' : ''}
                </div>
            </div>
            
            ${isUser ? `
                <div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                    </svg>
                </div>
            ` : ''}
        `;
        
        // Add event listener for SQL toggle button
        const sqlToggleBtn = messageDiv.querySelector('.sql-toggle-btn');
        if (sqlToggleBtn) {
            sqlToggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const sqlContainer = messageDiv.querySelector(`#sql-${messageId}`);
                if (sqlContainer) {
                    sqlContainer.classList.toggle('hidden');
                    const btnText = sqlToggleBtn.querySelector('span');
                    btnText.textContent = sqlContainer.classList.contains('hidden') ? 'View SQL Query' : 'Hide SQL Query';
                }
            });
        }
        
        return messageDiv;
    }

    formatMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showLoading() {
        const messagesContainer = document.getElementById('messages-container');
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading-indicator';
        loadingDiv.className = 'flex gap-4 p-4';
        loadingDiv.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                </svg>
            </div>
            <div class="bg-slate-100 border border-slate-200 rounded-2xl px-4 py-3">
                <div class="flex items-center gap-1">
                    <div class="w-2 h-2 bg-slate-400 rounded-full loading-dot"></div>
                    <div class="w-2 h-2 bg-slate-400 rounded-full loading-dot"></div>
                    <div class="w-2 h-2 bg-slate-400 rounded-full loading-dot"></div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(loadingDiv);
        this.scrollToBottom();
    }

    hideLoading() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    hideWelcomeScreen() {
        const welcomeScreen = document.getElementById('welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            const scrollArea = document.getElementById('message-scroll-area');
            if (scrollArea) {
                scrollArea.scrollTop = scrollArea.scrollHeight;
            }
        }, 100);
    }

    async assignGuestySessionId(session) {
        if (!session.guesty_session_id) {
            const newGuestyId = this.generateUniqueGuestySessionId();
            
            try {
                const response = await fetch(`/api/sessions/${session.id}/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        guesty_session_id: newGuestyId
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    // Update local session
                    const sessionIndex = this.sessions.findIndex(s => s.id === session.id);
                    if (sessionIndex !== -1) {
                        this.sessions[sessionIndex] = data;
                    }
                    this.renderSessions();
                } else {
                    console.error('Error assigning session ID:', data.error);
                }
            } catch (error) {
                console.error('Error assigning session ID:', error);
            }
        }
    }

    async deleteSession(sessionId) {
        try {
            const response = await fetch(`/api/sessions/${sessionId}/delete/`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // Remove session from local array
                const sessionIndex = this.sessions.findIndex(s => s.id === sessionId);
                if (sessionIndex !== -1) {
                    this.sessions.splice(sessionIndex, 1);
                }
                
                // If this was the current session, select another one or show welcome screen
                if (this.currentSession && this.currentSession.id === sessionId) {
                    if (this.sessions.length > 0) {
                        this.selectSession(this.sessions[0]);
                    } else {
                        this.currentSession = null;
                        this.messages = [];
                        this.renderMessages();
                        document.getElementById('welcome-screen').style.display = 'flex';
                    }
                }
                
                this.renderSessions();
            } else {
                const data = await response.json();
                console.error('Error deleting session:', data.error);
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }
}

// Initialize the chat application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new GuestyChat();
});