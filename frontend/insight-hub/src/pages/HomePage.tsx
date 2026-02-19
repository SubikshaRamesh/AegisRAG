import { useEffect, useMemo, useRef, useState } from "react";
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
import { SourceLink } from "@/components/SourceLink";
import { FilePreviewModal } from "@/components/FilePreviewModal";
import { extractErrorMessage } from "@/utils/errorHandler";


type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: Source[];
  isStreaming?: boolean; // Mark if this message is still streaming
};

const HomePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const chatId = searchParams.get("chatId");
  
  const [currentChatId, setCurrentChatId] = useState<string | null>(chatId);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isPlaying, setIsPlaying] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showNotes, setShowNotes] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewFilename, setPreviewFilename] = useState("");
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const createAndNavigateChat = async () => {
    const newChat = await api.createChat();
    setCurrentChatId(newChat.chat_id);
    setMessages([]);
    navigate(`/?chatId=${newChat.chat_id}`, { replace: true });
  };

  // ChatGPT-style typing animation
  const typeWriter = (text: string, metadata: any, speed = 10) => {
    setIsTyping(true);
    setStreamingAnswer("");
    let index = 0;

    const interval = setInterval(() => {
      index++;
      setStreamingAnswer(text.slice(0, index));

      if (index >= text.length) {
        clearInterval(interval);
        setIsTyping(false);

        // Push final assistant message to history AFTER typing completes
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: text,
            timestamp: new Date(),
            sources: metadata?.sources || [],
            confidence: metadata?.confidence,
          },
        ]);

        setStreamingAnswer("");
      }
    }, speed);
  };

  const loadConversation = async (id: string) => {
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
  };

  useEffect(() => {
    const initChat = async () => {
      try {
        if (chatId) {
          await loadConversation(chatId);
        } else {
          await createAndNavigateChat();
        }
      } catch (err) {
        console.error("Failed to initialize chat:", err);
        setError(extractErrorMessage(err));
        setIsChatLoading(false);
      }
    };

    initChat();
  }, [chatId, navigate]);

  const groupedMessages = useMemo(() => {
    return [...messages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [messages]);


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
    const first = files[0];

    try {
      setIsLoading(true);
      await api.uploadFile(first);
    } catch (uploadError) {
      setError(extractErrorMessage(uploadError));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !currentChatId) return;

    setError(null);
    setIsLoading(true);
    setStreamingAnswer("");
    setIsTyping(false);

    // Add user message immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userQuery = query;
    setQuery("");

    try {
      let fullText = ""; // Collect all tokens here
      let retrievedMetadata: any = null; // Store metadata for final message

      // Use streaming API
      await api.streamQuestion(
        userQuery,
        currentChatId,
        // onToken callback - collect tokens silently
        (token: string) => {
          fullText += token;
        },
        // onMetadata callback - store for later
        (metadata: any) => {
          retrievedMetadata = metadata;
        },
        // onError callback
        (error: Error) => {
          setError(`Streaming error: ${error.message}`);
          setStreamingAnswer("");
          setIsTyping(false);
        },
        // onComplete callback - start typing animation (which pushes message)
        () => {
          if (fullText) {
            typeWriter(fullText, retrievedMetadata, 10);
          }
        }
      );
    } catch (queryError) {
      setError(extractErrorMessage(queryError));
      setStreamingAnswer("");
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = async () => {
    try {
      setIsChatLoading(true);
      const newChat = await api.createChat();
      navigate(`/?chatId=${newChat.chat_id}`);
      setMessages([]);
      setError(null);
      setQuery("");
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

  const formatConfidence = (value?: number) => {
    if (value === undefined) return "N/A";
    return `${value.toFixed(1)}%`;
  };

  const confidenceClass = (value?: number) => {
    if (value === undefined) return "bg-muted text-muted-foreground";
    if (value >= 75) return "bg-emerald-500/15 text-emerald-300";
    if (value >= 45) return "bg-amber-500/15 text-amber-300";
    return "bg-rose-500/15 text-rose-300";
  };

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
        {messages.length === 0 && !isLoading && !isChatLoading && !isTyping && (
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

        {(isLoading || isChatLoading) && !isTyping && (
          <div className="bg-card rounded-2xl border border-border p-6 shadow-card">
            <div className="flex items-center gap-3">
              <Loader className="w-5 h-5 text-primary animate-spin" />
              <span className="text-sm text-muted-foreground">
                {isChatLoading ? "Loading chat..." : "Streaming response..."}
              </span>
            </div>
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        )}

        {/* Typing Animation Display - ABOVE message history */}
        {isTyping && (
          <div className="bg-card rounded-2xl border border-border p-6 shadow-card">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-3">
                <div className="text-foreground leading-relaxed whitespace-pre-wrap">
                  {streamingAnswer}
                  <span className="inline-block w-2 h-5 ml-1 bg-primary rounded-sm animate-cursor" />
                </div>
              </div>
            </div>
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
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex-1 space-y-3">
                    <div className="text-foreground leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                      {msg.isStreaming && (
                        <span className="inline-block w-2 h-5 ml-1 bg-primary rounded-sm animate-pulse" />
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {msg.confidence !== undefined && msg.confidence > 0 && (
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full ${confidenceClass(
                            msg.confidence
                          )}`}
                        >
                          Confidence {formatConfidence(msg.confidence)}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                  {!msg.isStreaming && (
                    <button
                      onClick={() => toggleVoice(msg.id)}
                      className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
                        isPlaying === msg.id
                          ? "gradient-sky text-primary-foreground shadow-sky"
                          : "bg-accent text-accent-foreground hover:bg-primary hover:text-primary-foreground"
                      }`}
                      title={isPlaying === msg.id ? "Stop reading" : "Read aloud"}
                    >
                      {isPlaying === msg.id ? (
                        <VolumeX className="w-5 h-5" />
                      ) : (
                        <Volume2 className="w-5 h-5" />
                      )}
                    </button>
                  )}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="border-t border-border pt-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                      Sources
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {msg.sources.map((source, i) => (
                        <SourceLink
                          key={`${source.source}-${i}`}
                          filename={source.source}
                          type={source.type}
                          score={source.score}
                          onPreview={handleOpenPreview}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Chat input */}
      <div className="p-4 border-t border-border bg-card">
        <form onSubmit={handleSend} className="flex gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your documents..."
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
            disabled={!query.trim() || isLoading}
            className="h-12 px-5 gradient-sky text-primary-foreground shadow-sky hover:opacity-90 transition-opacity rounded-xl"
          >
            <Send className="w-5 h-5" />
          </Button>
        </form>
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

      <button
        onClick={() => setShowNotes(false)}
        className="text-muted-foreground hover:text-foreground"
      >
        <X className="w-4 h-4" />
      </button>
    </div>

    <textarea
  value={noteText}
  onChange={(e) => setNoteText(e.target.value)}
  placeholder="Write your notes here..."
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

export default HomePage;
