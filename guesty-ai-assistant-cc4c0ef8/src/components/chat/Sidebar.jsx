import React from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Plus, MessageSquare, Building2, Sparkles, PanelLeftClose, PanelRightClose } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Sidebar({ 
  sessions, 
  currentSession, 
  onSessionSelect, 
  onNewChat, 
  isCollapsed,
  setSidebarCollapsed
}) {
  if (isCollapsed) {
    return (
      <motion.div 
        initial={{ width: 280 }}
        animate={{ width: 64 }}
        className="bg-slate-900 border-r border-slate-700 flex flex-col"
      >
        <div className="p-3 border-b border-slate-700 flex justify-center">
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarCollapsed(false)}
                className="text-slate-300 hover:bg-slate-700 hover:text-white"
            >
                <PanelRightClose className="w-5 h-5" />
            </Button>
        </div>
        <div className="flex-1 p-2 flex flex-col items-center">
            <Button
              onClick={onNewChat}
              size="icon"
              className="mb-4 bg-emerald-600 hover:bg-emerald-700"
            >
              <Plus className="w-4 h-4" />
            </Button>
            
            <div className="flex flex-col gap-2">
              {sessions.map((session) => (
                <Button
                  key={session.id}
                  variant={currentSession?.id === session.id ? "secondary" : "ghost"}
                  size="icon"
                  onClick={() => onSessionSelect(session)}
                  className={`rounded-full ${currentSession?.id === session.id ? "bg-slate-700" : "text-slate-300 hover:bg-slate-800 hover:text-white"}`}
                >
                  <MessageSquare className="w-4 h-4" />
                </Button>
              ))}
            </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      initial={{ width: 64 }}
      animate={{ width: 280 }}
      className="bg-slate-900 border-r border-slate-700 flex flex-col"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg flex items-center justify-center">
                    <Building2 className="w-4 h-4 text-white" />
                </div>
                <div>
                    <h2 className="font-semibold text-white">Guesty AI</h2>
                    <p className="text-xs text-slate-400">Property Assistant</p>
                </div>
            </div>
            <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarCollapsed(true)}
                className="text-slate-300 hover:bg-slate-700 hover:text-white"
            >
                <PanelLeftClose className="w-5 h-5" />
            </Button>
        </div>
        
        <Button
          onClick={onNewChat}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </Button>
      </div>

      {/* Chat Sessions */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1">
          <AnimatePresence>
            {sessions.map((session) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <Button
                  variant={currentSession?.id === session.id ? "secondary" : "ghost"}
                  className={`w-full justify-start text-left p-3 h-auto ${
                    currentSession?.id === session.id 
                      ? "bg-slate-700 text-white" 
                      : "text-slate-300 hover:text-white hover:bg-slate-800"
                  }`}
                  onClick={() => onSessionSelect(session)}
                >
                  <div className="flex items-start gap-3 w-full">
                    <MessageSquare className="w-4 h-4 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {session.title || `Chat ${session.session_id.slice(-4)}`}
                      </p>
                      <p className="text-xs text-slate-400 truncate mt-1">
                        {session.last_message || "No messages yet"}
                      </p>
                    </div>
                  </div>
                </Button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Sparkles className="w-3 h-3" />
          <span>Powered by Guesty AI</span>
        </div>
      </div>
    </motion.div>
  );
}