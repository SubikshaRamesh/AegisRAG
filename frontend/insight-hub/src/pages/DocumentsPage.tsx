// insight-hub/src/pages/DocumentsPage.tsx
import { useState, useMemo, useEffect } from "react";
import {
  Search,
  FileText,
  FileVideo,
  FileAudio,
  File,
  Download,
  Eye,
  FolderOpen,
  Grid3X3,
  List,
  Image as ImageIcon,
} from "lucide-react";
import { api } from "@/services/api";
import { FilePreviewModal } from "@/components/FilePreviewModal";
import type { FileInventoryItem } from "@/services/api";

interface Document {
  name: string;
  type: string;
  uploadedAt: string;
  chunks: number;
}

type FilterType = "all" | "video" | "text" | "image" | "audio";

// Helper function to infer file type from extension
const inferFileType = (filename: string): string => {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  
  // Video formats
  if (["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"].includes(ext)) {
    return "video";
  }
  
  // Audio formats
  if (["mp3", "wav", "ogg", "m4a", "flac", "aac", "wma"].includes(ext)) {
    return "audio";
  }
  
  // Image formats
  if (["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "ico"].includes(ext)) {
    return "image";
  }
  
  // Document/text formats
  if (["pdf", "doc", "docx", "txt", "rtf", "odt"].includes(ext)) {
    return "pdf";
  }
  
  if (["ppt", "pptx"].includes(ext)) {
    return "document";
  }
  
  return "text";
};

// Transform API response to Document format
const transformFileToDocument = (file: FileInventoryItem): Document => {
  const type = inferFileType(file.file_name);
  const uploadedAt = file.last_ingested_timestamp 
    ? new Date(file.last_ingested_timestamp).toISOString().split("T")[0]
    : "Unknown";
  
  return {
    name: file.file_name,
    type,
    uploadedAt,
    chunks: file.total_chunks,
  };
};

const getFileIcon = (type: string) => {
  switch (type) {
    case "video":
      return FileVideo;
    case "audio":
      return FileAudio;
    case "image":
      return ImageIcon;
    case "pdf":
    case "document":
    case "text":
      return FileText;
    default:
      return File;
  }
};

const getIconColor = (type: string) => {
  switch (type) {
    case "video":
      return "text-sky-600";
    case "audio":
      return "text-sky-500";
    case "image":
      return "text-emerald-500";
    default:
      return "text-primary";
  }
};

const isTextFile = (type: string) =>
  type === "text" || type === "pdf" || type === "document";

const DocumentsPage = () => {
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "list">("grid");
  const [filter, setFilter] = useState<FilterType>("all");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewFilename, setPreviewFilename] = useState("");

  // Fetch documents and system status on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch both documents and status in parallel
        const [filesResponse, status] = await Promise.all([
          api.getFiles(),
          api.getStatus(),
        ]);
        
        // Transform API response to Document format
        const transformedDocs = filesResponse.files.map(transformFileToDocument);
        setDocuments(transformedDocs);
        setSystemStatus(status);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load documents";
        setError(message);
        console.error("Failed to fetch documents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // counts
  const counts = useMemo(() => {
    return {
      all: documents.length,
      video: documents.filter((d) => d.type === "video").length,
      audio: documents.filter((d) => d.type === "audio").length,
      image: documents.filter((d) => d.type === "image").length,
      text: documents.filter((d) => isTextFile(d.type)).length,
    };
  }, [documents]);

  const filtered = useMemo(() => {
    return documents.filter((d) => {
      const matchSearch = d.name.toLowerCase().includes(search.toLowerCase());
      const matchFilter =
        filter === "all"
          ? true
          : filter === "video"
          ? d.type === "video"
          : filter === "audio"
          ? d.type === "audio"
          : filter === "image"
          ? d.type === "image"
          : isTextFile(d.type);

      return matchSearch && matchFilter;
    });
  }, [search, filter, documents]);

  const handleOpenDocument = (doc: Document) => {
    setPreviewFilename(doc.name);
    setIsPreviewOpen(true);
  };

  const handleDownloadDocument = (doc: Document) => {
    const link = document.createElement("a");
    link.href = `/api/files/${encodeURIComponent(doc.name)}`;
    link.download = doc.name;
    link.click();
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading documents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-rose-400 font-medium mb-2">Error loading documents</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header with system stats */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <FolderOpen className="w-6 h-6 text-primary" />
            Documents
          </h1>
          <p className="text-muted-foreground mt-1">
            {filtered.length} files shown
            {systemStatus && (
              <span className="ml-2 text-xs">
                (Total vectors: {systemStatus.text_vectors || 0} text, {systemStatus.image_vectors || 0} image)
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setView("grid")}
            className={`p-2 rounded-lg transition-colors ${
              view === "grid"
                ? "bg-accent text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Grid3X3 className="w-5 h-5" />
          </button>

          <button
            onClick={() => setView("list")}
            className={`p-2 rounded-lg transition-colors ${
              view === "list"
                ? "bg-accent text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search files by name..."
          className="w-full h-12 pl-12 pr-4 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/20 transition-all duration-200"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {[
          { key: "all", label: `All (${counts.all})` },
          { key: "video", label: `Video (${counts.video})` },
          { key: "text", label: `Text files (${counts.text})` },
          { key: "image", label: `Images (${counts.image})` },
          { key: "audio", label: `Voice (${counts.audio})` },
        ].map((item) => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key as FilterType)}
            className={`px-4 py-1.5 rounded-full text-sm border transition
              ${
                filter === item.key
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card border-border text-muted-foreground hover:text-foreground"
              }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Grid / List */}
      {view === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((doc) => {
            const Icon = getFileIcon(doc.type);

            return (
              <div
                key={doc.name}
                className="bg-card border border-border rounded-2xl p-5 shadow-card hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5 group"
              >
                <div className="w-12 h-12 rounded-xl bg-accent flex items-center justify-center mb-4">
                  <Icon className={`w-6 h-6 ${getIconColor(doc.type)}`} />
                </div>

                <h3 className="text-sm font-medium text-foreground truncate mb-1" title={doc.name}>
                  {doc.name}
                </h3>

                <p className="text-xs text-muted-foreground mb-2">
                  {doc.uploadedAt}
                </p>
                
                <p className="text-xs text-muted-foreground mb-4">
                  {doc.chunks} chunks processed
                </p>

                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  <button 
                    onClick={() => handleOpenDocument(doc)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent text-accent-foreground text-xs font-medium hover:bg-primary hover:text-primary-foreground transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Open
                  </button>

                  <button 
                    onClick={() => handleDownloadDocument(doc)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent text-accent-foreground text-xs font-medium hover:bg-primary hover:text-primary-foreground transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((doc) => {
            const Icon = getFileIcon(doc.type);

            return (
              <div
                key={doc.name}
                className="flex items-center gap-4 p-4 bg-card border border-border rounded-xl shadow-card hover:shadow-card-hover transition-all duration-200 group"
              >
                <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
                  <Icon className={`w-5 h-5 ${getIconColor(doc.type)}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {doc.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {doc.uploadedAt} · {doc.chunks} chunks
                  </p>
                </div>

                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => handleOpenDocument(doc)}
                    className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-primary transition-colors"
                    title="Open"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => handleDownloadDocument(doc)}
                    className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-primary transition-colors"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {filtered.length === 0 && documents.length === 0 && (
        <div className="text-center py-12">
          <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">No documents uploaded yet.</p>
        </div>
      )}

      {filtered.length === 0 && documents.length > 0 && (
        <div className="text-center py-12">
          <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">No documents match your search</p>
        </div>
      )}

      {/* File Preview Modal */}
      <FilePreviewModal
        isOpen={isPreviewOpen}
        filename={previewFilename}
        onClose={() => setIsPreviewOpen(false)}
      />
    </div>
  );
};

export default DocumentsPage;