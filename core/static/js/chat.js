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
            // For now, we'll use localStorage to simulate sessions
            const savedSessions = localStorage.getItem('guesty-chat-sessions');
            this.sessions = savedSessions ? JSON.parse(savedSessions) : [];
            
            // Migrate old sessions without guesty_session_id (optional - they can remain with null values)
            this.sessions.forEach(session => {
                if (!session.guesty_session_id) {
                    // Old sessions keep their original structure, guesty_session_id remains undefined/null
                    console.log(`Legacy session found: ${session.id} - no Guesty session ID assigned`);
                }
            });
            
            this.renderSessions();
            
            if (this.sessions.length > 0 && !this.currentSession) {
                this.selectSession(this.sessions[0]);
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
            session_id: internalId, // Keep for backward compatibility
            guesty_session_id: guestySessionId,
            title: "New Chat",
            message_count: 0,
            last_message: "",
            created_date: new Date().toISOString()
        };

        this.sessions.unshift(newSession);
        this.saveSessions();
        this.renderSessions();
        this.selectSession(newSession);
    }

    selectSession(session) {
        this.currentSession = session;
        this.loadMessages(session.session_id);
        this.renderSessions();
        this.hideWelcomeScreen();
    }

    async loadMessages(sessionId) {
        try {
            const savedMessages = localStorage.getItem(`guesty-chat-messages-${sessionId}`);
            this.messages = savedMessages ? JSON.parse(savedMessages) : [];
            this.renderMessages();
            this.scrollToBottom();
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
            // Add user message
            const userMessage = {
                id: Date.now(),
                session_id: this.currentSession.session_id,
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

            // Simulate AI response (replace with actual API call later)
            const aiResponse = await this.generateAIResponse(content);
            
            const aiMessage = {
                id: Date.now() + 1,
                session_id: this.currentSession.session_id,
                content: aiResponse,
                role: "assistant",
                timestamp: new Date().toISOString()
            };

            this.messages.push(aiMessage);
            this.hideLoading();
            this.renderMessages();
            this.scrollToBottom();

            // Update session
            this.currentSession.last_message = content.substring(0, 100);
            this.currentSession.message_count = this.messages.filter(m => m.session_id === this.currentSession.session_id).length;
            
            if (this.currentSession.message_count === 2) { // First exchange
                this.currentSession.title = content.substring(0, 50);
            }

            this.saveSessions();
            this.saveMessages();
            this.renderSessions();

        } catch (error) {
            console.error('Error sending message:', error);
            this.hideLoading();
        } finally {
            this.isLoading = false;
        }
    }

    async generateAIResponse(userMessage) {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

        // Simple responses for demonstration (replace with actual API call)
        const responses = [
            "Thank you for your question about property management. As your Guesty AI assistant, I'm here to help you optimize your short-term rental operations. Could you provide more specific details about your property or the challenge you're facing?",
            "Great question! For property management best practices, I recommend focusing on guest communication, automated check-in processes, and regular property maintenance schedules. What specific aspect would you like me to elaborate on?",
            "I understand you're looking for guidance on revenue optimization. Key strategies include dynamic pricing, seasonal adjustments, and analyzing competitor rates in your area. Would you like me to dive deeper into any of these areas?",
            "That's an excellent point about guest experience. Providing clear instructions, quick response times, and anticipating guest needs are crucial for positive reviews and repeat bookings. How can I help you implement these strategies?",
            "For cleaning and maintenance coordination, I suggest creating detailed checklists, establishing reliable vendor relationships, and implementing quality control processes. What's your current setup, and where do you see room for improvement?"
        ];

        return responses[Math.floor(Math.random() * responses.length)];
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
                </div>
                <div class="text-xs text-slate-400 mt-1 ${isUser ? 'text-right' : 'text-left'}">
                    ${timestamp}
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
        
        return messageDiv;
    }

    formatMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
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

    assignGuestySessionId(session) {
        if (!session.guesty_session_id) {
            session.guesty_session_id = this.generateUniqueGuestySessionId();
            this.saveSessions();
            this.renderSessions();
        }
        return session.guesty_session_id;
    }

    deleteSession(sessionId) {
        const sessionIndex = this.sessions.findIndex(s => s.id === sessionId);
        if (sessionIndex !== -1) {
            const session = this.sessions[sessionIndex];
            
            // Remove session messages from localStorage
            localStorage.removeItem(`guesty-chat-messages-${session.session_id}`);
            
            // Remove session from array
            this.sessions.splice(sessionIndex, 1);
            
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
            
            this.saveSessions();
            this.renderSessions();
        }
    }

    saveSessions() {
        localStorage.setItem('guesty-chat-sessions', JSON.stringify(this.sessions));
    }

    saveMessages() {
        if (this.currentSession) {
            const sessionMessages = this.messages.filter(m => m.session_id === this.currentSession.session_id);
            localStorage.setItem(`guesty-chat-messages-${this.currentSession.session_id}`, JSON.stringify(sessionMessages));
        }
    }
}

// Initialize the chat application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new GuestyChat();
});
