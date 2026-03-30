import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";

import {
  Download,
  MessageSquare,
  Send,
  Sparkles,
  StickyNote,
  Upload,
  Volume2,
  VolumeX,
  X,
  Plus,
  Loader,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, ApiError, Source } from "@/services/api";
import { FilePreviewModal } from "@/components/FilePreviewModal";
import { extractErrorMessage } from "@/utils/errorHandler";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: Source[];
  isStreaming?: boolean;
};

const HomePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const chatId = searchParams.get("chatId");

  // Use a ref in addition to state so handleSend always reads the latest value
  // without needing to be re-created every time currentChatId changes.
  const currentChatIdRef = useRef<string | null>(null);
  const [currentChatId, _setCurrentChatId] = useState<string | null>(null);
  const setCurrentChatId = useCallback((id: string | null) => {
    currentChatIdRef.current = id;
    _setCurrentChatId(id);
  }, []);

  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isPlaying, setIsPlaying] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showNotes, setShowNotes] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewFilename, setPreviewFilename] = useState("");

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const createAndNavigateChat = useCallback(async () => {
    const newChat = await api.createChat();
    setCurrentChatId(newChat.chat_id);
    setMessages([]);
    navigate(`/?chatId=${newChat.chat_id}`, { replace: true });
    return newChat.chat_id;
  }, [navigate, setCurrentChatId]);

  const loadConversation = useCallback(async (id: string) => {
    setIsChatLoading(true);
    try {
      const chatData = await api.loadConversation(id);
      const loadedMessages = chatData.messages.map((msg) => ({
        id: crypto.randomUUID(),
        role: msg.role as "user" | "assistant",
        content: msg.content,
        timestamp: new Date(msg.timestamp * 1000),
        sources: msg.sources,
      }));
      setMessages(loadedMessages);
      setCurrentChatId(id);
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 404) {
        console.warn(`Chat ${id} not found, creating new chat`);
        await createAndNavigateChat();
        return;
      }
      console.error("Failed to load conversation:", loadError);
      setError(extractErrorMessage(loadError));
    } finally {
      setIsChatLoading(false);
    }
  }, [createAndNavigateChat, setCurrentChatId]);

  // Initialize chat on mount / when chatId URL param changes
  useEffect(() => {
    let cancelled = false;

    const initChat = async () => {
      try {
        if (chatId) {
          await loadConversation(chatId);
        } else {
          await createAndNavigateChat();
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to initialize chat:", err);
          setError(extractErrorMessage(err));
          setIsChatLoading(false);
        }
      }
    };

    initChat();
    return () => { cancelled = true; };
  }, [chatId]); // intentionally only re-run when chatId changes

  const groupedMessages = useMemo(
    () => [...messages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime()),
    [messages]
  );

  const downloadNote = () => {
    if (!noteText.trim()) return;
    const blob = new Blob([noteText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "my-note.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleHomeFiles = async (files: FileList) => {
    if (!files.length) return;
    setError(null);
    try {
      setIsLoading(true);
      await api.uploadFile(files[0]);
    } catch (uploadError) {
      setError(extractErrorMessage(uploadError));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Read from ref so we always have the latest chatId
    // even if the state update hasn't re-rendered yet.
    let activeChatId = currentChatIdRef.current;

    // If there's somehow no chat yet, create one before sending
    if (!activeChatId) {
      try {
        setIsChatLoading(true);
        activeChatId = await createAndNavigateChat();
      } catch (err) {
        setError("Could not start a chat. Please try again.");
        setIsChatLoading(false);
        return;
      } finally {
        setIsChatLoading(false);
      }
    }

    setError(null);
    setIsLoading(true);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    const assistantMessageId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        sources: [],
        confidence: undefined,
        isStreaming: true,
      },
    ]);

    const userQuery = query;
    setQuery("");

    const findAssistantMessageIndex = (messagesList: Message[]) => {
      for (let i = messagesList.length - 1; i >= 0; i--) {
        if (messagesList[i].id === assistantMessageId) {
          return i;
        }
      }
      return -1;
    };

    try {
      await api.streamQuestion(
        userQuery,
        activeChatId,
        (token: string) => {
          const trimmedToken = token.trim();
          if (
            trimmedToken.startsWith("{") &&
            /(type|chat_id|retrieval_time)\s*:/.test(trimmedToken)
          ) {
            return;
          }

          setMessages((prev) => {
            const updated = [...prev];
            const assistantIndex = findAssistantMessageIndex(updated);
            if (assistantIndex === -1) return prev;

            const target = updated[assistantIndex];
            updated[assistantIndex] = {
              ...target,
              content: target.content + token,
            };
            return updated;
          });
        },
        (metadata) => {
          setMessages((prev) => {
            const updated = [...prev];
            const assistantIndex = findAssistantMessageIndex(updated);
            if (assistantIndex === -1) return prev;

            const target = updated[assistantIndex];
            const nextContent =
              typeof metadata.answer === "string" && metadata.answer.trim() && !target.content.trim()
                ? metadata.answer
                : target.content;

            updated[assistantIndex] = {
              ...target,
              content: nextContent,
              sources: Array.isArray(metadata.sources) ? metadata.sources : target.sources,
              confidence:
                typeof metadata.confidence === "number"
                  ? metadata.confidence
                  : target.confidence,
            };
            return updated;
          });
        },
        (err: Error) => {
          setError(`Streaming error: ${err.message}`);
          setMessages((prev) => {
            const updated = [...prev];
            const assistantIndex = findAssistantMessageIndex(updated);
            if (assistantIndex === -1) return prev;
            updated[assistantIndex] = {
              ...updated[assistantIndex],
              isStreaming: false,
            };
            return updated;
          });
        },
        () => {
          setMessages((prev) => {
            const updated = [...prev];
            const assistantIndex = findAssistantMessageIndex(updated);
            if (assistantIndex === -1) return prev;
            updated[assistantIndex] = {
              ...updated[assistantIndex],
              isStreaming: false,
            };
            return updated;
          });
        }
      );
    } catch (queryError) {
      setError(extractErrorMessage(queryError));
      setMessages((prev) => {
        const updated = [...prev];
        const assistantIndex = findAssistantMessageIndex(updated);
        if (assistantIndex === -1) return prev;
        updated[assistantIndex] = {
          ...updated[assistantIndex],
          isStreaming: false,
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = async () => {
    try {
      setIsChatLoading(true);
      const newChat = await api.createChat();
      setCurrentChatId(newChat.chat_id);
      setMessages([]);
      setError(null);
      setQuery("");
      navigate(`/?chatId=${newChat.chat_id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsChatLoading(false);
    }
  };

  const toggleVoice = (id: string) => {
    if (isPlaying === id) {
      setIsPlaying(null);
      window.speechSynthesis.cancel();
    } else {
      const msg = messages.find((m) => m.id === id);
      if (msg) {
        const utterance = new SpeechSynthesisUtterance(msg.content);
        utterance.lang = "en-US";
        utterance.onend = () => setIsPlaying(null);
        window.speechSynthesis.speak(utterance);
        setIsPlaying(id);
      }
    }
  };

  const handleOpenPreview = (filename: string) => {
    setPreviewFilename(filename);
    setIsPreviewOpen(true);
  };

  const getSourcePage = (source: Source): number | undefined => {
    const sourceWithPage = source as Source & { metadata?: { page?: number } };
    if (typeof sourceWithPage.page === "number") return sourceWithPage.page;
    if (typeof sourceWithPage.metadata?.page === "number") return sourceWithPage.metadata.page;
    return undefined;
  };

  const formatConfidence = (value?: number) =>
    value === undefined ? "N/A" : `${value.toFixed(1)}%`;

  const confidenceClass = (value?: number) => {
    if (value === undefined) return "bg-muted text-muted-foreground";
    if (value >= 75) return "bg-emerald-500/15 text-emerald-300";
    if (value >= 45) return "bg-amber-500/15 text-amber-300";
    return "bg-rose-500/15 text-rose-300";
  };

  // Disable send only while actively loading — NOT while isChatLoading
  // because the handler now auto-creates a chat if needed.
  const sendDisabled = !query.trim() || isLoading;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border bg-card flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            Ask Your Documents
          </h1>
          <p className="text-muted-foreground mt-1">
            Query your uploaded files and get AI-powered answers
          </p>
        </div>
        <Button
          onClick={handleNewChat}
          disabled={isChatLoading}
          className="h-10 px-4 gradient-sky text-primary-foreground shadow-sky hover:opacity-90 transition-opacity rounded-xl flex items-center gap-2"
          title="Start a new chat"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </Button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {messages.length === 0 && !isLoading && !isChatLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-accent flex items-center justify-center mb-6">
              <MessageSquare className="w-10 h-10 text-primary" />
            </div>
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Start a conversation
            </h2>
            <p className="text-muted-foreground max-w-sm">
              Ask any question about your uploaded documents and get instant, intelligent responses.
            </p>
          </div>
        )}

        {isChatLoading && (
          <div className="bg-card rounded-2xl border border-border p-6 shadow-card">
            <div className="flex items-center gap-3">
              <Loader className="w-5 h-5 text-primary animate-spin" />
              <span className="text-sm text-muted-foreground">Loading chat…</span>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200 flex items-center justify-between gap-3">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-rose-300 hover:text-rose-100">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {groupedMessages.map((msg) => (
          <div key={msg.id} className="space-y-4">
            {msg.role === "user" ? (
              <div className="flex justify-end">
                <div className="bg-primary text-primary-foreground px-5 py-3 rounded-2xl rounded-br-md max-w-lg shadow-sky">
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ) : (
              <div className="bg-card rounded-2xl border border-border p-6 shadow-card hover:shadow-card-hover transition-shadow duration-300">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-4">
                    <div className="text-foreground leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                      {msg.isStreaming && (
                        <span className="inline-block w-2 h-4 ml-1 bg-primary rounded-sm animate-cursor" />
                      )}
                    </div>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Sources
                        </p>
                        <ul className="space-y-2">
                          {msg.sources.map((source, i) => {
                            const page = getSourcePage(source);
                            const label = page ? `${source.source} (Page ${page})` : source.source;
                            return (
                              <li key={`${source.source}-${i}`} className="flex items-start gap-2">
                                <span className="text-xs text-muted-foreground mt-1">•</span>
                                <button
                                  type="button"
                                  onClick={() => handleOpenPreview(source.source)}
                                  className="text-xs px-2.5 py-1 rounded-full bg-accent text-accent-foreground hover:bg-primary hover:text-primary-foreground transition"
                                >
                                  {label}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center gap-2">
                      {msg.confidence !== undefined && msg.confidence > 0 && !msg.isStreaming && (
                        <span className={`text-xs px-2.5 py-1 rounded-full ${confidenceClass(msg.confidence)}`}>
                          Confidence: {formatConfidence(msg.confidence)}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground">{msg.timestamp.toLocaleTimeString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleVoice(msg.id)}
                    className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
                      isPlaying === msg.id
                        ? "gradient-sky text-primary-foreground shadow-sky"
                        : "bg-accent text-accent-foreground hover:bg-primary hover:text-primary-foreground"
                    }`}
                    title={isPlaying === msg.id ? "Stop reading" : "Read aloud"}
                  >
                    {isPlaying === msg.id ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat input */}
      <div className="p-4 border-t border-border bg-card">
        <form onSubmit={handleSend} className="flex gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                // Allow Shift+Enter for newlines; plain Enter submits
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!sendDisabled) handleSend(e as any);
                }
              }}
              placeholder="Ask a question about your documents…"
              className="w-full h-12 pl-5 pr-12 rounded-xl bg-muted border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 transition-all duration-200"
            />

            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => e.target.files && handleHomeFiles(e.target.files)}
            />

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition"
              title="Upload files"
            >
              <Upload className="w-5 h-5" />
            </button>
          </div>

          <Button
            type="submit"
            disabled={sendDisabled}
            className="h-12 px-5 gradient-sky text-primary-foreground shadow-sky hover:opacity-90 transition-opacity rounded-xl"
          >
            <Send className="w-5 h-5" />
          </Button>
        </form>

        {/* Show chat ID status for debugging — remove in production */}
        {!currentChatId && !isChatLoading && (
          <p className="text-xs text-center text-amber-400 mt-2">
            No active chat — your message will auto-create one.
          </p>
        )}
      </div>

      {/* Floating Note Bubble */}
      <button
        onClick={() => setShowNotes(true)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center hover:scale-105 transition"
        title="Take notes"
      >
        <StickyNote className="w-6 h-6" />
      </button>

      {/* Notes Popup */}
      {showNotes && (
        <div className="fixed bottom-24 right-6 z-50 w-80 h-[50vh] bg-background border border-border rounded-xl shadow-xl p-4 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm">Quick Notes</h3>
            <button onClick={() => setShowNotes(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-4 h-4" />
            </button>
          </div>

          <textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Write your notes here…"
            className="w-full flex-1 resize-none rounded-md border border-border bg-muted p-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={downloadNote}
              className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>
      )}

      <FilePreviewModal
        isOpen={isPreviewOpen}
        filename={previewFilename}
        onClose={() => setIsPreviewOpen(false)}
      />
    </div>
  );
};

export default HomePage