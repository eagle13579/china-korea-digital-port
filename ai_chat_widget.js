/**
 * AI Chat Widget — 中韩出海数智港 AI 客服聊天组件
 * =====================================================
 * 纯 JS 文件，可嵌入到任何页面。
 *
 * 用法：
 *   <script src="/path/to/ai_chat_widget.js"></script>
 *   <script>
 *     AIChatWidget.init({
 *       apiUrl: 'http://localhost:5198',
 *       position: 'right',     // 'right' | 'left'
 *       title: 'AI客服',
 *       subtitle: '在线咨询',
 *       avatar: '🤖',
 *       autoOpen: false,
 *     });
 *   </script>
 *
 * 按 Ctrl+Enter 发送消息，Enter 为换行。
 */

(function (global) {
  'use strict';

  // ── 默认配置 ──────────────────────────────────────────
  var DEFAULTS = {
    apiUrl: 'http://localhost:5198',
    position: 'right',
    title: 'AI 客服',
    subtitle: '在线咨询',
    avatar: '🤖',
    autoOpen: false,
    primaryColor: '#4f46e5',
    welcomeDelay: 500,
  };

  // ── 语言检测 ──────────────────────────────────────────
  function detectLanguage() {
    var lang = (navigator.language || navigator.userLanguage || 'zh').toLowerCase();
    if (lang.startsWith('ko')) return 'ko';
    if (lang.startsWith('zh')) return 'zh';
    return 'en';
  }

  // ── 欢迎消息（三语） ──────────────────────────────────
  var WELCOME_MESSAGES = {
    zh: '您好！我是中韩出海数智港的AI客服助手。有什么可以帮您的吗？😊',
    ko: '안녕하세요! 한중 해외 진출 디지털 포트의 AI 고객 서비스 어시스턴트입니다. 무엇을 도와드릴까요? 😊',
    en: 'Hello! I\'m the AI customer service assistant of China-Korea Digital Port. How can I help you? 😊',
  };

  var INPUT_PLACEHOLDERS = {
    zh: '输入消息...',
    ko: '메시지를 입력하세요...',
    en: 'Type a message...',
  };

  // ── DOM 工具 ──────────────────────────────────────────
  function createEl(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'style' && typeof attrs[k] === 'object') {
          Object.keys(attrs[k]).forEach(function (sk) {
            el.style[sk] = attrs[k][sk];
          });
        } else if (k === 'className') {
          el.className = attrs[k];
        } else if (k.startsWith('on')) {
          el.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        } else {
          el.setAttribute(k, attrs[k]);
        }
      });
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(function (c) {
        if (typeof c === 'string') {
          el.appendChild(document.createTextNode(c));
        } else if (c) {
          el.appendChild(c);
        }
      });
    }
    return el;
  }

  // ── 样式 ──────────────────────────────────────────────
  var STYLES = {
    container: {
      position: 'fixed',
      bottom: '24px',
      zIndex: '2147483647',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    },
    bubble: {
      width: '56px',
      height: '56px',
      borderRadius: '50%',
      background: '#4f46e5',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      boxShadow: '0 4px 12px rgba(79,70,229,0.4)',
      transition: 'all 0.3s ease',
      fontSize: '24px',
      border: 'none',
      userSelect: 'none',
    },
    bubbleHover: {
      transform: 'scale(1.1)',
      boxShadow: '0 6px 20px rgba(79,70,229,0.5)',
    },
    window: {
      position: 'absolute',
      bottom: '72px',
      width: '360px',
      height: '520px',
      background: '#1a1a2e',
      borderRadius: '16px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      display: 'none',
      flexDirection: 'column',
      overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.08)',
    },
    header: {
      padding: '16px 20px',
      background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flexShrink: 0,
    },
    headerAvatar: {
      width: '36px',
      height: '36px',
      borderRadius: '50%',
      background: 'rgba(255,255,255,0.2)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '18px',
    },
    headerInfo: {
      flex: 1,
    },
    headerTitle: {
      color: '#fff',
      fontWeight: 600,
      fontSize: '15px',
      lineHeight: '1.3',
    },
    headerSubtitle: {
      color: 'rgba(255,255,255,0.7)',
      fontSize: '12px',
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
    statusDot: {
      width: '6px',
      height: '6px',
      borderRadius: '50%',
      background: '#22c55e',
      display: 'inline-block',
    },
    closeBtn: {
      background: 'rgba(255,255,255,0.15)',
      border: 'none',
      color: '#fff',
      width: '28px',
      height: '28px',
      borderRadius: '50%',
      cursor: 'pointer',
      fontSize: '16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'background 0.2s',
    },
    messages: {
      flex: 1,
      overflowY: 'auto',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      background: '#1a1a2e',
    },
    messageRow: {
      display: 'flex',
      maxWidth: '85%',
    },
    botMessage: {
      alignSelf: 'flex-start',
    },
    userMessage: {
      alignSelf: 'flex-end',
      flexDirection: 'row-reverse',
    },
    messageBubble: {
      padding: '10px 14px',
      borderRadius: '14px',
      fontSize: '14px',
      lineHeight: '1.5',
      wordBreak: 'break-word',
      whiteSpace: 'pre-wrap',
    },
    botBubble: {
      background: '#2d2d44',
      color: '#e2e8f0',
      borderBottomLeftRadius: '4px',
    },
    userBubble: {
      background: '#4f46e5',
      color: '#fff',
      borderBottomRightRadius: '4px',
    },
    timestamp: {
      fontSize: '10px',
      color: 'rgba(255,255,255,0.35)',
      marginTop: '4px',
      textAlign: 'right',
    },
    inputArea: {
      padding: '12px 16px',
      background: '#1e1e36',
      borderTop: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      gap: '8px',
      alignItems: 'flex-end',
      flexShrink: 0,
    },
    input: {
      flex: 1,
      background: '#2d2d44',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '10px',
      padding: '10px 14px',
      color: '#e2e8f0',
      fontSize: '14px',
      outline: 'none',
      resize: 'none',
      maxHeight: '120px',
      fontFamily: 'inherit',
      lineHeight: '1.4',
    },
    sendBtn: {
      background: '#4f46e5',
      border: 'none',
      color: '#fff',
      width: '42px',
      height: '42px',
      borderRadius: '10px',
      cursor: 'pointer',
      fontSize: '18px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s',
      flexShrink: 0,
    },
    sendBtnDisabled: {
      opacity: 0.4,
      cursor: 'not-allowed',
    },
    loadingDots: {
      display: 'flex',
      gap: '4px',
      padding: '8px 4px',
    },
    loadingDot: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: '#6b7280',
      animation: 'aiChatBounce 1.4s infinite ease-in-out both',
    },
    scrollbar: {
      '&::-webkit-scrollbar': { width: '6px' },
      '&::-webkit-scrollbar-track': { background: 'transparent' },
      '&::-webkit-scrollbar-thumb': { background: 'rgba(255,255,255,0.15)', borderRadius: '3px' },
    },
  };

  // ── 主组件 ─────────────────────────────────────────────
  function AIChatWidget(options) {
    this.config = {};
    for (var k in DEFAULTS) this.config[k] = DEFAULTS[k];
    if (options) {
      for (var k in options) this.config[k] = options[k];
    }

    this.language = detectLanguage();
    this.messages = [];
    this.isOpen = false;
    this.isLoading = false;
    this.container = null;
    this.windowEl = null;
    this.messagesEl = null;
    this.inputEl = null;
    this.sendBtn = null;
    this.bubbleBtn = null;

    this._init();
  }

  AIChatWidget.prototype._init = function () {
    this._injectKeyframes();
    this._buildDOM();
    this._bindEvents();

    if (this.config.autoOpen) {
      setTimeout(this.open.bind(this), 300);
    }
  };

  AIChatWidget.prototype._injectKeyframes = function () {
    if (document.getElementById('ai-chat-widget-keyframes')) return;
    var style = document.createElement('style');
    style.id = 'ai-chat-widget-keyframes';
    style.textContent =
      '@keyframes aiChatBounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } } ' +
      '@keyframes aiChatFadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } } ' +
      '.ai-chat-msg-enter { animation: aiChatFadeIn 0.3s ease-out both; } ' +
      '.ai-chat-typing-indicator span { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #6b7280; margin: 0 2px; animation: aiChatBounce 1.4s infinite ease-in-out both; } ' +
      '.ai-chat-typing-indicator span:nth-child(1) { animation-delay: -0.32s; } ' +
      '.ai-chat-typing-indicator span:nth-child(2) { animation-delay: -0.16s; }';
    document.head.appendChild(style);
  };

  AIChatWidget.prototype._buildDOM = function () {
    var self = this;
    var cfg = this.config;

    // ── 容器 ──
    this.container = createEl('div', {
      style: {
        position: 'fixed',
        bottom: '24px',
        zIndex: '2147483647',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      }
    });
    this.container.style[cfg.position] = '24px';

    // ── 聊天窗口 ──
    this.windowEl = createEl('div', {
      style: {
        position: 'absolute',
        bottom: '72px',
        width: '360px',
        height: '520px',
        background: '#1a1a2e',
        borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        display: 'none',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.08)',
      }
    });
    if (cfg.position === 'left') {
      this.windowEl.style.left = '0';
    } else {
      this.windowEl.style.right = '0';
    }

    // ── Header ──
    var header = createEl('div', {
      style: {
        padding: '16px 20px',
        background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        flexShrink: 0,
      }
    });

    var avatar = createEl('div', {
      style: {
        width: '36px',
        height: '36px',
        borderRadius: '50%',
        background: 'rgba(255,255,255,0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '18px',
      }
    }, cfg.avatar);

    var info = createEl('div', { style: { flex: 1 } });
    var title = createEl('div', { style: { color: '#fff', fontWeight: 600, fontSize: '15px', lineHeight: '1.3' } }, cfg.title);
    var statusRow = createEl('div', {
      style: { color: 'rgba(255,255,255,0.7)', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }
    });
    statusRow.appendChild(createEl('span', { style: { width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e', display: 'inline-block' } }));
    statusRow.appendChild(document.createTextNode(cfg.subtitle));
    info.appendChild(title);
    info.appendChild(statusRow);

    var closeBtn = createEl('button', {
      style: {
        background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff', width: '28px', height: '28px',
        borderRadius: '50%', cursor: 'pointer', fontSize: '16px', display: 'flex', alignItems: 'center',
        justifyContent: 'center', transition: 'background 0.2s',
      },
      on: { click: function () { self.close(); } }
    }, '✕');

    header.appendChild(avatar);
    header.appendChild(info);
    header.appendChild(closeBtn);

    // ── 消息区域 ──
    this.messagesEl = createEl('div', {
      style: {
        flex: 1, overflowY: 'auto', padding: '16px',
        display: 'flex', flexDirection: 'column', gap: '10px', background: '#1a1a2e',
      }
    });

    // ── 输入区域 ──
    this.inputEl = createEl('textarea', {
      style: {
        flex: 1, background: '#2d2d44', border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '10px', padding: '10px 14px', color: '#e2e8f0', fontSize: '14px',
        outline: 'none', resize: 'none', maxHeight: '120px', fontFamily: 'inherit', lineHeight: '1.4',
      },
      placeholder: INPUT_PLACEHOLDERS[this.language] || 'Type a message...',
      rows: 1,
      on: {
        keydown: function (e) {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            self._sendMessage();
          }
        },
        input: function () {
          self._autoResize();
          self._updateSendButton();
        },
      }
    });

    this.sendBtn = createEl('button', {
      style: {
        background: '#4f46e5', border: 'none', color: '#fff', width: '42px', height: '42px',
        borderRadius: '10px', cursor: 'pointer', fontSize: '18px', display: 'flex',
        alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s', flexShrink: 0,
        opacity: 0.4, cursor: 'not-allowed',
      },
      on: { click: function () { self._sendMessage(); } }
    });
    this.sendBtn.innerHTML = '↑';

    var inputArea = createEl('div', {
      style: {
        padding: '12px 16px', background: '#1e1e36', borderTop: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', gap: '8px', alignItems: 'flex-end', flexShrink: 0,
      }
    });
    inputArea.appendChild(this.inputEl);
    inputArea.appendChild(this.sendBtn);

    this.windowEl.appendChild(header);
    this.windowEl.appendChild(this.messagesEl);
    this.windowEl.appendChild(inputArea);

    // ── 气泡按钮 ──
    this.bubbleBtn = createEl('button', {
      style: {
        width: '56px', height: '56px', borderRadius: '50%', background: '#4f46e5',
        display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(79,70,229,0.4)', transition: 'all 0.3s ease',
        fontSize: '24px', border: 'none', userSelect: 'none',
      },
      on: {
        click: function () { self.toggle(); },
        mouseenter: function () {
          this.style.transform = 'scale(1.1)';
          this.style.boxShadow = '0 6px 20px rgba(79,70,229,0.5)';
        },
        mouseleave: function () {
          this.style.transform = 'scale(1)';
          this.style.boxShadow = '0 4px 12px rgba(79,70,229,0.4)';
        },
      }
    }, '💬');

    this.container.appendChild(this.windowEl);
    this.container.appendChild(this.bubbleBtn);
    document.body.appendChild(this.container);
  };

  AIChatWidget.prototype._bindEvents = function () {
    // 点击空白区域关闭
    var self = this;
    document.addEventListener('click', function (e) {
      if (self.isOpen && !self.container.contains(e.target)) {
        self.close();
      }
    });
  };

  AIChatWidget.prototype._autoResize = function () {
    this.inputEl.style.height = 'auto';
    var newH = Math.min(this.inputEl.scrollHeight, 120);
    this.inputEl.style.height = newH + 'px';
  };

  AIChatWidget.prototype._updateSendButton = function () {
    var hasText = this.inputEl.value.trim().length > 0;
    this.sendBtn.style.opacity = hasText ? '1' : '0.4';
    this.sendBtn.style.cursor = hasText ? 'pointer' : 'not-allowed';
    this.sendBtn.disabled = !hasText;
  };

  AIChatWidget.prototype._addMessage = function (text, role) {
    var msgDiv = createEl('div', {
      style: {
        display: 'flex',
        maxWidth: '85%',
        alignSelf: role === 'bot' ? 'flex-start' : 'flex-end',
        flexDirection: role === 'user' ? 'row-reverse' : 'row',
      },
      className: 'ai-chat-msg-enter',
    });

    var bubble = createEl('div', {
      style: {
        padding: '10px 14px', borderRadius: '14px', fontSize: '14px',
        lineHeight: '1.5', wordBreak: 'break-word', whiteSpace: 'pre-wrap',
      }
    }, text);
    if (role === 'bot') {
      bubble.style.background = '#2d2d44';
      bubble.style.color = '#e2e8f0';
      bubble.style.borderBottomLeftRadius = '4px';
    } else {
      bubble.style.background = '#4f46e5';
      bubble.style.color = '#fff';
      bubble.style.borderBottomRightRadius = '4px';
    }

    msgDiv.appendChild(bubble);
    this.messagesEl.appendChild(msgDiv);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;

    this.messages.push({ text: text, role: role });
  };

  AIChatWidget.prototype._showTyping = function () {
    var typing = createEl('div', {
      style: {
        display: 'flex', maxWidth: '85%', alignSelf: 'flex-start',
        padding: '10px 14px', borderRadius: '14px', background: '#2d2d44',
        borderBottomLeftRadius: '4px',
      },
      className: 'ai-chat-msg-enter ai-chat-typing-indicator',
      id: 'ai-chat-typing',
    });
    typing.appendChild(createEl('span'));
    typing.appendChild(createEl('span'));
    typing.appendChild(createEl('span'));
    this.messagesEl.appendChild(typing);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  };

  AIChatWidget.prototype._removeTyping = function () {
    var typing = document.getElementById('ai-chat-typing');
    if (typing) typing.remove();
  };

  AIChatWidget.prototype._sendMessage = function () {
    if (this.isLoading) return;
    var text = this.inputEl.value.trim();
    if (!text) return;

    this._addMessage(text, 'user');
    this.inputEl.value = '';
    this._autoResize();
    this._updateSendButton();

    this._showTyping();
    this.isLoading = true;

    var self = this;
    var xhr = new XMLHttpRequest();
    xhr.open('POST', this.config.apiUrl + '/api/chat', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        self._removeTyping();
        self.isLoading = false;
        var reply = '';
        try {
          var data = JSON.parse(xhr.responseText);
          reply = data.reply || '⚠️ 抱歉，暂时无法回复。';
        } catch (e) {
          reply = '⚠️ 网络连接异常，请稍后再试。';
        }
        self._addMessage(reply, 'bot');
      }
    };
    xhr.onerror = function () {
      self._removeTyping();
      self.isLoading = false;
      self._addMessage('⚠️ 网络连接异常，请检查网络后重试。', 'bot');
    };
    xhr.send(JSON.stringify({
      message: text,
      language: this.language,
    }));
  };

  AIChatWidget.prototype._sendWelcome = function () {
    var self = this;
    setTimeout(function () {
      self._addMessage(WELCOME_MESSAGES[self.language] || WELCOME_MESSAGES['zh'], 'bot');
    }, this.config.welcomeDelay);
  };

  // ── 公开 API ──────────────────────────────────────────
  AIChatWidget.prototype.open = function () {
    if (this.isOpen) return;
    this.windowEl.style.display = 'flex';
    this.bubbleBtn.style.display = 'none';
    this.isOpen = true;

    if (this.messages.length === 0) {
      this._sendWelcome();
    }

    setTimeout(function () {
      if (self.inputEl) self.inputEl.focus();
    }, 300);
    var self = this;
  };

  AIChatWidget.prototype.close = function () {
    if (!this.isOpen) return;
    this.windowEl.style.display = 'none';
    this.bubbleBtn.style.display = 'flex';
    this.isOpen = false;
  };

  AIChatWidget.prototype.toggle = function () {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  };

  AIChatWidget.prototype.destroy = function () {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  };

  // ── 全局导出 ──────────────────────────────────────────
  var instances = [];

  global.AIChatWidget = {
    init: function (options) {
      var widget = new AIChatWidget(options);
      instances.push(widget);
      return widget;
    },
    getInstances: function () {
      return instances;
    },
  };
})(window);
