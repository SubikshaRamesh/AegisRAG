import { useEffect, useMemo, useState } from "react";
import { Clock, MessageSquare, ChevronRight, Search } from "lucide-react";

import { api, HistoryMessage } from "@/services/api";

interface ChatHistoryItem {
  id: string;
  query: string;
  preview: string;
  timestamp: string;
  sources: number;
}

const HistoryPage = () => {
  const [history, setHistory] = useState<HistoryMessage[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sessionId = sessionStorage.getItem("aegisrag_session_id");
    if (!sessionId) {
      setIsLoading(false);
      return;
    }

    const loadHistory = async () => {
      try {
        const response = await api.getHistory(sessionId);
        setHistory(response.history || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load history");
      } finally {
        setIsLoading(false);
      }
    };

    loadHistory();
  }, []);

  const items = useMemo<ChatHistoryItem[]>(() => {
    return history
      .filter((msg) => msg.role === "assistant")
      .map((msg, index) => {
        const query = history[index * 2]?.content || "Question";
        const preview = msg.content.slice(0, 160) + (msg.content.length > 160 ? "..." : "");
        const date = msg.timestamp ? new Date(msg.timestamp * 1000) : new Date();

        return {
          id: `${index}-${date.getTime()}`,
          query,
          preview,
          timestamp: date.toLocaleString(),
          sources: 0,
        };
      })
      .filter((item) => {
        if (!search.trim()) return true;
        return (
          item.query.toLowerCase().includes(search.toLowerCase()) ||
          item.preview.toLowerCase().includes(search.toLowerCase())
        );
      });
  }, [history, search]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Clock className="w-6 h-6 text-primary" />
          Chat History
        </h1>
        <p className="text-muted-foreground mt-1">
          Your previous conversations and queries
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          placeholder="Search your history..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-full h-12 pl-12 pr-4 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 transition-all duration-200"
        />
      </div>

      {/* History list */}
      <div className="space-y-3">
        {isLoading && (
          <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Loading session history...
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        )}
        {!isLoading && !error && items.length === 0 && (
          <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            No session history found yet.
          </div>
        )}
        {items.map((item) => (
          <button
            key={item.id}
            className="w-full text-left p-5 bg-card border border-border rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5 group"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                <MessageSquare className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-4 mb-1">
                  <h3 className="text-sm font-semibold text-foreground truncate">
                    {item.query}
                  </h3>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {item.timestamp}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {item.preview}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs px-2 py-0.5 rounded-md bg-accent text-accent-foreground">
                    {item.sources} source{item.sources > 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-2" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default HistoryPage;
