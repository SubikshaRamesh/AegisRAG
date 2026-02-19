export interface Source {
  type: "pdf" | "image" | "audio" | "video" | "docx" | "unknown" | string;
  source: string;
  score: number;
}

export interface QueryResponse {
  chat_id: string;
  answer: string;
  confidence: number;
  sources: Source[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  sources?: Source[];
}

export interface ChatHistory {
  chat_id: string;
  messages: ChatMessage[];
}

export interface CreateChatResponse {
  chat_id: string;
  created_at: string;
}

export interface ConversationItem {
  chat_id: string;
  title: string;
  created_at: string;
}

export interface ListConversationsResponse {
  status: string;
  conversations: ConversationItem[];
}

export interface UploadResponse {
  status: string;
  filename: string;
  file_type: string;
  chunks_extracted: number;
  chunks_added: number;
  duplicates_skipped: number;
  processing_time_seconds: number;
  message: string;
}

export interface HealthStatus {
  status: string;
  text_vectors: number;
  image_vectors: number;
}

export interface StatusResponse {
  status: string;
  text_embedder: string;
  clip_embedder: string;
  llm_model: string;
  text_vectors: number;
  image_vectors: number;
  vector_dim: {
    text: number;
    image: number;
  };
}

export interface FileInventoryItem {
  file_name: string;
  total_chunks: number;
  first_ingested_timestamp: string;
  last_ingested_timestamp: string;
}

export interface FilesInventoryResponse {
  status: string;
  count: number;
  files: FileInventoryItem[];
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}



class ApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`/api${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const message = error.detail || `API request failed: ${response.statusText}`;
      throw new ApiError(message, response.status);
    }

    return response.json();
  }

  async createChat(): Promise<CreateChatResponse> {
    return this.request("/chat/new", { method: "POST" });
  }

  async loadConversation(chatId: string): Promise<ChatHistory> {
    return this.request(`/history/${encodeURIComponent(chatId)}`);
  }

  async listConversations(limit: number = 50, offset: number = 0): Promise<ListConversationsResponse> {
    const query = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
    return this.request(`/history?${query}`);
  }

  async askQuestion(question: string, chatId: string): Promise<QueryResponse> {
    return this.request("/query", {
      method: "POST",
      body: JSON.stringify({ question, chat_id: chatId }),
    });
  }

  async streamQuestion(
    question: string,
    chatId: string,
    onToken: (token: string) => void,
    onMetadata?: (metadata: any) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    try {
      const response = await fetch("/api/stream-query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, chat_id: chatId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body not readable");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          // Process any remaining buffer
          if (buffer.trim()) {
            this._processStreamChunk(buffer.trim(), onToken, onMetadata, onError);
          }
          onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines from buffer
        const lines = buffer.split("\n\n");
        buffer = lines[lines.length - 1]; // Keep incomplete line in buffer

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith("data: ")) {
            const data = line.slice(6); // Remove "data: " prefix
            if (data && data !== "[DONE]") {
              this._processStreamChunk(data, onToken, onMetadata, onError);
            }
          }
        }
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      onError?.(err);
    }
  }

  private _processStreamChunk(
    data: string,
    onToken: (token: string) => void,
    onMetadata?: (metadata: any) => void,
    onError?: (error: Error) => void
  ): void {
    try {
      // Try to parse as JSON (metadata)
      const parsed = JSON.parse(data);
      if (parsed.type === "metadata") {
        onMetadata?.(parsed);
      } else if (parsed.type === "error") {
        onError?.(new Error(parsed.message || "Unknown error"));
      }
    } catch {
      // Not JSON, treat as token text
      onToken(data);
    }
  }

  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
          } else {
            reject(new Error(data.detail || "Upload failed"));
          }
        } catch (error) {
          reject(new Error("Upload failed"));
        }
      };

      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.send(formData);
    });
  }

  async healthCheck(): Promise<HealthStatus> {
    return this.request("/health");
  }

  async getStatus(): Promise<StatusResponse> {
    return this.request("/status");
  }

  async getFiles(): Promise<FilesInventoryResponse> {
    return this.request("/files");
  }
}

export const api = new ApiService();