import React from "react";
import { motion } from "framer-motion";
import { User, Bot, Building2 } from "lucide-react";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";

export default function MessageBubble({ message, isLast }) {
  const isUser = message.role === "user";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-4 p-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4 h-4 text-white" />
        </div>
      )}
      
      <div className={`max-w-[80%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-emerald-600 text-white ml-auto"
              : "bg-slate-100 text-slate-900 border border-slate-200"
          }`}
        >
          <div className="prose prose-sm max-w-none">
            {isUser ? (
              <p className="mb-0 text-white">{message.content}</p>
            ) : (
              <ReactMarkdown 
                className="mb-0 prose-slate prose-sm"
                components={{
                  p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({children}) => <ul className="mb-2 ml-4">{children}</ul>,
                  ol: ({children}) => <ol className="mb-2 ml-4">{children}</ol>,
                  li: ({children}) => <li className="mb-1">{children}</li>,
                  strong: ({children}) => <strong className="font-semibold text-slate-800">{children}</strong>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        </div>
        
        <div className={`text-xs text-slate-400 mt-1 ${isUser ? "text-right" : "text-left"}`}>
          {message.timestamp && format(new Date(message.timestamp), "HH:mm")}
        </div>
      </div>
      
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </motion.div>
  );
}