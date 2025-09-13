import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import io from 'socket.io-client';
import axios from 'axios';
import { 
  MessageCircle, 
  Send, 
  Bot, 
  Users, 
  Settings, 
  Zap,
  Sparkles,
  CircuitBoard,
  Wifi,
  User
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Initialize socket connection
const socket = io(BACKEND_URL, {
  forceNew: true,
  transports: ['websocket', 'polling']
});

// Debug Socket.IO connection
window.socket = socket;

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [typingUsers, setTypingUsers] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [showSetup, setShowSetup] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Socket event handlers
  useEffect(() => {
    socket.on('connect', () => {
      setIsConnected(true);
      console.log('Connected to server');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('Disconnected from server');
    });

    socket.on('new_message', (message) => {
      setMessages(prev => [...prev, message]);
      scrollToBottom();
    });

    socket.on('user_typing', (data) => {
      if (data.typing) {
        setTypingUsers(prev => [...prev.filter(u => u.user_id !== data.user_id), data]);
      } else {
        setTypingUsers(prev => prev.filter(u => u.user_id !== data.user_id));
      }
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    try {
      const userData = { username, email };
      const response = await axios.post(`${API}/users`, userData);
      setCurrentUser(response.data);
      
      // Create a default conversation
      const convResponse = await axios.post(`${API}/conversations`, {
        name: "General Chat",
        participants: [response.data.id]
      });
      
      setConversations([convResponse.data]);
      setActiveConversation(convResponse.data);
      socket.emit('join_conversation', { conversation_id: convResponse.data.id });
      
      // Load messages
      loadMessages(convResponse.data.id);
      setShowSetup(false);
    } catch (error) {
      console.error('Setup failed:', error);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      const response = await axios.get(`${API}/conversations/${conversationId}/messages`);
      setMessages(response.data);
      setTimeout(scrollToBottom, 100);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !currentUser || !activeConversation) return;

    try {
      const messageData = {
        content: newMessage,
        sender_id: currentUser.id,
        sender_username: currentUser.username,
        conversation_id: activeConversation.id
      };

      await axios.post(`${API}/messages`, messageData);
      setNewMessage('');
      
      // Stop typing indicator
      socket.emit('typing_stop', {
        conversation_id: activeConversation.id,
        user_id: currentUser.id
      });
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const sendAIMessage = async () => {
    if (!newMessage.trim() || !currentUser || !activeConversation) return;

    try {
      const messageData = {
        content: newMessage,
        sender_id: currentUser.id,
        sender_username: currentUser.username,
        conversation_id: activeConversation.id
      };

      // Send user message first
      await axios.post(`${API}/messages`, messageData);
      
      // Get AI response
      await axios.post(`${API}/ai/chat`, messageData);
      
      setNewMessage('');
    } catch (error) {
      console.error('Failed to get AI response:', error);
    }
  };

  const handleTyping = (e) => {
    setNewMessage(e.target.value);
    
    if (!isTyping && currentUser && activeConversation) {
      setIsTyping(true);
      socket.emit('typing_start', {
        conversation_id: activeConversation.id,
        user_id: currentUser.id,
        username: currentUser.username
      });
    }

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      socket.emit('typing_stop', {
        conversation_id: activeConversation.id,
        user_id: currentUser.id
      });
    }, 1000);
  };

  if (showSetup) {
    return (
      <div className="setup-container">
        <div className="setup-background"></div>
        <motion.div 
          className="setup-card"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="setup-header">
            <div className="logo">
              <CircuitBoard className="logo-icon" />
              <h1>OmniChat</h1>
            </div>
            <p>Bem-vindo ao futuro da comunicação</p>
          </div>
          
          <form onSubmit={handleSetup} className="setup-form">
            <div className="input-group">
              <User className="input-icon" />
              <input
                type="text"
                placeholder="Seu nome de usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className="input-group">
              <MessageCircle className="input-icon" />
              <input
                type="email"
                placeholder="Seu email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            
            <motion.button
              type="submit"
              className="setup-button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Zap className="button-icon" />
              Iniciar Chat
            </motion.button>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <motion.div 
        className="sidebar"
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="sidebar-header">
          <div className="logo">
            <CircuitBoard className="logo-icon" />
            <span>OmniChat</span>
          </div>
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <Wifi size={16} />
            <span>{isConnected ? 'Online' : 'Offline'}</span>
          </div>
        </div>

        <div className="user-info">
          <div className="user-avatar">
            <User size={24} />
          </div>
          <div className="user-details">
            <span className="username">{currentUser?.username}</span>
            <span className="user-status">Ativo</span>
          </div>
        </div>

        <div className="conversations-list">
          {conversations.map((conv) => (
            <motion.div
              key={conv.id}
              className={`conversation-item ${activeConversation?.id === conv.id ? 'active' : ''}`}
              onClick={() => {
                setActiveConversation(conv);
                loadMessages(conv.id);
                socket.emit('join_conversation', { conversation_id: conv.id });
              }}
              whileHover={{ x: 5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <Users size={20} />
              <div className="conversation-info">
                <span className="conversation-name">{conv.name}</span>
                <span className="last-message">{conv.last_message || "Sem mensagens"}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Main Chat Area */}
      <div className="chat-main">
        {activeConversation ? (
          <>
            {/* Chat Header */}
            <motion.div 
              className="chat-header"
              initial={{ y: -50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <div className="chat-info">
                <h2>{activeConversation.name}</h2>
                <span className="participants-count">
                  {activeConversation.participants.length} participantes
                </span>
              </div>
              <div className="chat-actions">
                <motion.button 
                  className="action-btn"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <Settings size={20} />
                </motion.button>
              </div>
            </motion.div>

            {/* Messages Area */}
            <div className="messages-container">
              <div className="messages-list">
                <AnimatePresence>
                  {messages.map((message, index) => (
                    <motion.div
                      key={message.id}
                      className={`message ${message.sender_id === currentUser?.id ? 'own' : ''} ${message.message_type === 'ai_response' ? 'ai' : ''}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      {message.message_type === 'ai_response' && (
                        <div className="message-ai-indicator">
                          <Bot size={16} />
                          <Sparkles size={14} />
                        </div>
                      )}
                      <div className="message-content">
                        <div className="message-header">
                          <span className="sender-name">{message.sender_username}</span>
                          <span className="message-time">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="message-text">{message.content}</p>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {/* Typing Indicator */}
                <AnimatePresence>
                  {typingUsers.length > 0 && (
                    <motion.div
                      className="typing-indicator"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                    >
                      <div className="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                      <span className="typing-text">
                        {typingUsers[0].username} está digitando...
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Message Input */}
            <motion.div 
              className="message-input-container"
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <form onSubmit={sendMessage} className="message-form">
                <div className="input-wrapper">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={handleTyping}
                    placeholder="Digite sua mensagem..."
                    className="message-input"
                  />
                  <div className="input-actions">
                    <motion.button
                      type="button"
                      onClick={sendAIMessage}
                      className="ai-button"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      title="Perguntar para IA"
                    >
                      <Bot size={20} />
                    </motion.button>
                    <motion.button
                      type="submit"
                      className="send-button"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      <Send size={20} />
                    </motion.button>
                  </div>
                </div>
              </form>
            </motion.div>
          </>
        ) : (
          <div className="no-conversation">
            <CircuitBoard size={64} />
            <h3>Selecione uma conversa</h3>
            <p>Escolha uma conversa para começar a chatear</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;