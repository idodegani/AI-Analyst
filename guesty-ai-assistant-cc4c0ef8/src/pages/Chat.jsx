
import React, { useState, useEffect, useRef, useCallback } from "react";
import { ChatSession, ChatMessage } from "@/api/entities";
import { InvokeLLM } from "@/api/integrations";
import { ScrollArea } from "@/components/ui/scroll-area";
import { motion, AnimatePresence } from "framer-motion";

import Sidebar from "../components/chat/Sidebar";
import MessageBubble from "../components/chat/MessageBubble";
import LoadingDots from "../components/chat/LoadingDots";
import MessageInput from "../components/chat/MessageInput";

export default function Chat() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef(null);

  const loadSessions = useCallback(async () => {
    try {
      const sessionList = await ChatSession.list("-updated_date");
      setSessions(sessionList);
      
      // Check if currentSession is still valid
      if (currentSession) {
        const isCurrentSessionInList = sessionList.some(s => s.id === currentSession.id);
        if (!isCurrentSessionInList) {
          setCurrentSession(sessionList.length > 0 ? sessionList[0] : null);
        }
      } else if (sessionList.length > 0) {
        setCurrentSession(sessionList[0]);
      }
    } catch (error) {
      console.error("Error loading sessions:", error);
    }
  }, [currentSession]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (currentSession) {
      loadMessages(currentSession.session_id);
    } else {
      setMessages([]); // Clear messages if no session is selected
    }
  }, [currentSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadMessages = async (sessionId) => {
    try {
      const messageList = await ChatMessage.filter(
        { session_id: sessionId },
        "created_date"
      );
      setMessages(messageList);
    } catch (error) {
      console.error("Error loading messages:", error);
      setMessages([]);
    }
  };

  const createNewSession = async () => {
    try {
      const sessionId = `gs_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const newSession = await ChatSession.create({
        session_id: sessionId,
        title: "New Chat",
        message_count: 0
      });
      
      await loadSessions(); // Reload sessions to get the new one at the top
      setCurrentSession(newSession); // Set the new session as current
      return newSession; // Return the new session for immediate use
    } catch (error) {
      console.error("Error creating session:", error);
      return null;
    }
  };

  const handleSendMessage = async (content) => {
    let sessionToUpdate = currentSession;
    if (!sessionToUpdate) {
        sessionToUpdate = await createNewSession();
    }

    if (!sessionToUpdate) {
        console.error("Failed to create or find a session.");
        return;
    }

    try {
      // Add user message first
      const userMessage = await ChatMessage.create({
        session_id: sessionToUpdate.session_id,
        content,
        role: "user",
        timestamp: new Date().toISOString()
      });

      // Update UI with user message immediately
      setMessages(prev => [...prev, userMessage]);

      // Now show loading for AI response
      setIsLoading(true);

      // Generate AI response with Guesty context
      const prompt = `You are Guesty AI, an intelligent assistant specialized in short-term rental property management. You help property managers, Airbnb hosts, and vacation rental businesses with:

- Property operations and maintenance
- Guest communication and support
- Reservation management
- Revenue optimization
- Booking platform management
- Task automation
- Reporting and analytics
- Cleaning and housekeeping coordination
- Pricing strategies
- Guest experience improvement

Provide helpful, specific, and actionable advice related to property management. Be professional yet friendly.

User question: ${content}`;

      const response = await InvokeLLM({
        prompt,
        add_context_from_internet: false
      });

      // Add AI response
      const aiMessage = await ChatMessage.create({
        session_id: sessionToUpdate.session_id,
        content: response,
        role: "assistant",
        timestamp: new Date().toISOString()
      });

      setMessages(prev => [...prev, aiMessage]);

      // Update session with last message and count
      const updatedTitle = sessionToUpdate.message_count === 0 ? content.substring(0, 50) : sessionToUpdate.title;
      await ChatSession.update(sessionToUpdate.id, {
        last_message: content.substring(0, 100),
        message_count: messages.length + 2, // Account for both user and AI message
        title: updatedTitle
      });

      // Refresh sessions list
      loadSessions();

    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSessionSelect = (session) => {
    setCurrentSession(session);
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar
        sessions={sessions}
        currentSession={currentSession}
        onSessionSelect={handleSessionSelect}
        onNewChat={createNewSession}
        isCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <ScrollArea className="flex-1" id="message-scroll-area">
          <div className="max-w-4xl mx-auto pt-8">
            {messages.length === 0 && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center h-full min-h-[calc(100vh-200px)] text-center px-4"
              >
                <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl flex items-center justify-center mb-6">
                  <span className="text-2xl font-bold text-white">G</span>
                </div>
                
                {currentSession ? (
                  <>
                    <h2 className="text-3xl font-bold text-slate-800 mb-3">
                      Hey, welcome to Guesty AI!
                    </h2>
                    <p className="text-lg text-slate-600 mb-6 max-w-md">
                      How can I help?
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="text-2xl font-bold text-slate-800 mb-3">
                      Welcome to Guesty AI
                    </h2>
                    <p className="text-slate-600 mb-6 max-w-md">
                      Your intelligent assistant for property management. Start a new chat or select one to begin.
                    </p>
                  </>
                )}

                {!currentSession &&
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
                    {[
                      "How do I handle guest complaints effectively?",
                      "What's the best pricing strategy for my property?",
                      "Help me automate check-in processes",
                      "How to improve my property's occupancy rate?"
                    ].map((suggestion, index) => (
                      <motion.button
                        key={index}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => handleSendMessage(suggestion)}
                        className="text-left p-3 bg-white border border-slate-200 rounded-lg hover:border-emerald-300 hover:bg-emerald-50 text-sm text-slate-700 transition-colors"
                      >
                        {suggestion}
                      </motion.button>
                    ))}
                  </div>
                }
              </motion.div>
            )}

            <AnimatePresence>
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isLast={message.id === messages[messages.length - 1]?.id}
                />
              ))}
            </AnimatePresence>

            {isLoading && <LoadingDots />}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <MessageInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          disabled={false} // Message input should always be enabled, new session is created if none exists.
        />
      </div>
    </div>
  );
}
