import { useEffect, useMemo, useRef, useState } from "react";

import {
  Download,
  FileText,
  MessageSquare,
  Send,
  Sparkles,
  StickyNote,
  Upload,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, Source } from "@/services/api";


type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: number;
  sources?: Source[];
};

const HomePage = () => {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isPlaying, setIsPlaying] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showNotes, setShowNotes] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    const existing = sessionStorage.getItem("aegisrag_session_id");
    if (existing) {
      setSessionId(existing);
      return;
    }

    const generated = crypto.randomUUID();
    sessionStorage.setItem("aegisrag_session_id", generated);
    setSessionId(generated);
  }, []);

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
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !sessionId) return;

    setError(null);
    setIsLoading(true);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery("");

    try {
      const response = await api.askQuestion(query, sessionId);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        timestamp: new Date(),
        confidence: response.confidence,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (queryError) {
      setError(queryError instanceof Error ? queryError.message : "Query failed");
    } finally {
      setIsLoading(false);
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
        utterance.onend = () => setIsPlaying(null);
        window.speechSynthesis.speak(utterance);
        setIsPlaying(id);
      }
    }
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
      <div className="p-6 border-b border-border bg-card">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-primary" />
          Ask Your Documents
        </h1>
        <p className="text-muted-foreground mt-1">
          Query your uploaded files and get AI-powered answers
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {messages.length === 0 && !isLoading && (
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

        {isLoading && (
          <div className="bg-card rounded-2xl border border-border p-6 shadow-card animate-pulse">
            <div className="h-4 bg-muted rounded w-3/4 mb-3" />
            <div className="h-4 bg-muted rounded w-1/2 mb-3" />
            <div className="h-4 bg-muted rounded w-2/3" />
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
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
                    <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-xs px-2.5 py-1 rounded-full ${confidenceClass(
                          msg.confidence
                        )}`}
                      >
                        Confidence {formatConfidence(msg.confidence)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {msg.timestamp.toLocaleTimeString()}
                      </span>
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
                    {isPlaying === msg.id ? (
                      <VolumeX className="w-5 h-5" />
                    ) : (
                      <Volume2 className="w-5 h-5" />
                    )}
                  </button>
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="border-t border-border pt-4">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                      Sources
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {msg.sources.map((source, i) => (
                        <div
                          key={`${source.source}-${i}`}
                          className="rounded-xl border border-border/80 bg-muted/40 p-3 text-sm"
                        >
                          <div className="flex items-center gap-2 text-foreground">
                            <FileText className="w-4 h-4 text-primary" />
                            <span className="truncate">{source.source}</span>
                          </div>
                          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                            <span className="uppercase">{source.type}</span>
                            <span>Score {source.score.toFixed(1)}%</span>
                          </div>
                        </div>
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

    </div>
  );
};

export default HomePage;
