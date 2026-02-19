import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, MessageSquare, ChevronRight, Search } from "lucide-react";

import { api, ConversationItem } from "@/services/api";
import { extractErrorMessage } from "@/utils/errorHandler";

const HistoryPage = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const response = await api.listConversations();
        setConversations(response.conversations || []);
      } catch (err) {
        setError(extractErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    };

    loadConversations();
  }, []);

  const filteredConversations = useMemo(() => {
    return conversations.filter((conv) => {
      if (!search.trim()) return true;
      return conv.title.toLowerCase().includes(search.toLowerCase());
    });
  }, [conversations, search]);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

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
          placeholder="Search your chats..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-full h-12 pl-12 pr-4 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 transition-all duration-200"
        />
      </div>

      {/* Conversations list */}
      <div className="space-y-3">
        {isLoading && (
          <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Loading chat history...
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        )}
        {!isLoading && !error && conversations.length === 0 && (
          <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            No chat history yet. Start a new chat to begin!
          </div>
        )}
        {!isLoading && !error && filteredConversations.length === 0 && conversations.length > 0 && (
          <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            No conversations match your search.
          </div>
        )}
        {filteredConversations.map((conv) => (
          <button
            key={conv.chat_id}
            onClick={() => navigate(`/?chatId=${encodeURIComponent(conv.chat_id)}`, { replace: false })}
            className="w-full text-left p-5 bg-card border border-border rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5 group cursor-pointer"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                <MessageSquare className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-4 mb-1">
                  <h3 className="text-sm font-semibold text-foreground truncate">
                    {conv.title}
                  </h3>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatDate(conv.created_at)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  ID: {conv.chat_id.substring(0, 8)}...
                </p>
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
