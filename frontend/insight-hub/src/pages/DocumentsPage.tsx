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
  BarChart3,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  RadialBarChart,
  RadialBar,
} from "recharts";
import { api } from "@/services/api";

interface Document {
  id: number;
  name: string;
  type: string;
  size: string;
  uploadedAt: string;
  category: string;
  chunks?: number;
}

type FilterType = "all" | "video" | "text" | "image" | "audio";

// ── palette ──────────────────────────────────────────────────────────────────
const TYPE_META: Record<string, { label: string; color: string; gradient: [string, string] }> = {
  video:    { label: "Video",    color: "#38bdf8", gradient: ["#38bdf8", "#0ea5e9"] },
  audio:    { label: "Audio",    color: "#a78bfa", gradient: ["#a78bfa", "#7c3aed"] },
  image:    { label: "Images",   color: "#34d399", gradient: ["#34d399", "#059669"] },
  pdf:      { label: "PDF",      color: "#fb923c", gradient: ["#fb923c", "#ea580c"] },
  document: { label: "Docs",     color: "#f472b6", gradient: ["#f472b6", "#db2777"] },
  text:     { label: "Text",     color: "#facc15", gradient: ["#facc15", "#ca8a04"] },
};

const getTypeMeta = (type: string) =>
  TYPE_META[type] ?? { label: "Other", color: "#94a3b8", gradient: ["#94a3b8", "#64748b"] };

const getFileIcon = (type: string) => {
  switch (type) {
    case "video":    return FileVideo;
    case "audio":    return FileAudio;
    case "image":    return ImageIcon;
    case "pdf":
    case "document":
    case "text":     return FileText;
    default:         return File;
  }
};

const isTextFile = (type: string) =>
  type === "text" || type === "pdf" || type === "document";

const defaultUploadedAt = () => new Date().toISOString().split("T")[0];

const normalizeType = (typeValue: unknown, nameValue: unknown): string => {
  const type = String(typeValue ?? "").toLowerCase().trim();
  if (type) {
    if (["doc", "docx", "txt", "md"].includes(type)) return "document";
    if (["jpg", "jpeg", "png", "gif", "webp"].includes(type)) return "image";
    return type;
  }

  const name = String(nameValue ?? "").toLowerCase();
  const extension = name.includes(".") ? name.split(".").pop() ?? "" : "";

  if (["pdf"].includes(extension)) return "pdf";
  if (["doc", "docx", "txt", "md"].includes(extension)) return "document";
  if (["mp4", "mov", "avi", "mkv", "webm"].includes(extension)) return "video";
  if (["mp3", "wav", "m4a", "aac", "ogg"].includes(extension)) return "audio";
  if (["jpg", "jpeg", "png", "gif", "webp"].includes(extension)) return "image";

  return "text";
};

const toSizeLabel = (sizeValue: unknown): string => {
  if (typeof sizeValue === "number" && Number.isFinite(sizeValue)) {
    if (sizeValue < 1024) {
      return `${sizeValue.toFixed(1)} KB`;
    }
    return `${(sizeValue / 1024).toFixed(1)} MB`;
  }

  if (typeof sizeValue === "string" && sizeValue.trim().length > 0) {
    return sizeValue;
  }

  return "0 KB";
};

const toCategory = (categoryValue: unknown, type: string): string => {
  if (typeof categoryValue === "string" && categoryValue.trim().length > 0) {
    return categoryValue;
  }

  if (type === "video") return "Video";
  if (type === "audio") return "Audio";
  if (type === "image") return "Images";
  if (isTextFile(type)) return "Docs";
  return "Docs";
};

const normalizeDocumentsResponse = (payload: unknown): Document[] => {
  const response = payload as { documents?: unknown; files?: unknown };
  const rawList = Array.isArray(response?.documents)
    ? response.documents
    : Array.isArray(response?.files)
      ? response.files
      : [];

  return rawList.map((item, index) => {
    const raw = (item ?? {}) as Record<string, unknown>;

    const name = String(raw.name ?? raw.file_name ?? `document-${index + 1}`);
    const type = normalizeType(raw.type ?? raw.file_type, name);
    const uploadedAtRaw = raw.uploadedAt ?? raw.uploaded_at ?? raw.first_ingested_timestamp;
    const uploadedAt =
      typeof uploadedAtRaw === "string" && uploadedAtRaw.length >= 10
        ? uploadedAtRaw.slice(0, 10)
        : defaultUploadedAt();

    const parsedChunks = Number(raw.chunks ?? raw.total_chunks);
    const hasChunks = Number.isFinite(parsedChunks);

    return {
      id: Number(raw.id) || index + 1,
      name,
      type,
      size: toSizeLabel(raw.size),
      uploadedAt,
      category: toCategory(raw.category, type),
      ...(hasChunks ? { chunks: parsedChunks } : {}),
    };
  });
};

// ── Custom tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-2.5 shadow-lg text-sm">
      <p className="font-semibold text-foreground">{payload[0].name}</p>
      <p className="text-muted-foreground">{payload[0].value} file{payload[0].value !== 1 ? "s" : ""}</p>
    </div>
  );
};

// ── Custom Pie label ──────────────────────────────────────────────────────────
const PieLabel = ({ cx, cy, midAngle, outerRadius, name, value }: any) => {
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 28;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  if (value === 0) return null;
  return (
    <text x={x} y={y} fill="currentColor" textAnchor={x > cx ? "start" : "end"} dominantBaseline="central"
      className="text-xs fill-muted-foreground font-medium">
      {name} ({value})
    </text>
  );
};

// ── ANALYTICS SECTION ─────────────────────────────────────────────────────────
const AnalyticsSection = ({ documents }: { documents: Document[] }) => {
  // Aggregate by type group
  const typeGroups = useMemo(() => {
    const map: Record<string, number> = {};
    documents.forEach((d) => {
      const key = isTextFile(d.type) ? d.type : d.type;
      map[key] = (map[key] || 0) + 1;
    });
    return Object.entries(map).map(([type, count]) => ({
      type,
      name: getTypeMeta(type).label,
      value: count,
      color: getTypeMeta(type).color,
    }));
  }, [documents]);

  const totalChunks = useMemo(
    () => documents.reduce((acc, d) => acc + (d.chunks || 0), 0),
    [documents]
  );

  // Parse sizes to MB for bar chart
  const sizeData = useMemo(() =>
    documents.map((d) => {
      const raw = parseFloat(d.size);
      const unit = d.size.includes("KB") ? 0.001 : 1;
      return { name: d.name.split(".")[0].slice(0, 14), size: parseFloat((raw * unit).toFixed(2)), color: getTypeMeta(d.type).color };
    }), [documents]);

  // Radial bar data (chunks)
  const radialData = useMemo(() =>
    documents
      .filter((d) => d.chunks)
      .map((d) => ({ name: d.name.split(".")[0].slice(0, 12), chunks: d.chunks!, fill: getTypeMeta(d.type).color }))
      .sort((a, b) => b.chunks - a.chunks),
    [documents]
  );

  return (
    <div className="space-y-4">
      {/* Stat pills */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Files", value: documents.length, icon: FolderOpen, accent: "#38bdf8" },
          { label: "Total Chunks", value: totalChunks, icon: BarChart3, accent: "#a78bfa" },
          { label: "File Types", value: typeGroups.length, icon: Grid3X3, accent: "#34d399" },
          { label: "Categories", value: [...new Set(documents.map((d) => d.category))].length, icon: List, accent: "#fb923c" },
        ].map((stat) => (
          <div key={stat.label}
            className="bg-card border border-border rounded-2xl p-4 flex items-center gap-3 shadow-card"
            style={{ borderLeft: `3px solid ${stat.accent}` }}>
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: `${stat.accent}18` }}>
              <stat.icon className="w-4 h-4" style={{ color: stat.accent }} />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground leading-none">{stat.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* ── Donut chart ── */}
        <div className="bg-card border border-border rounded-2xl p-5 shadow-card">
          <p className="text-sm font-semibold text-foreground mb-1">File Type Distribution</p>
          <p className="text-xs text-muted-foreground mb-4">Breakdown by file category</p>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={typeGroups}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
                labelLine={false}
                label={PieLabel}
              >
                {typeGroups.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-3">
            {typeGroups.map((g) => (
              <div key={g.type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="w-2 h-2 rounded-full" style={{ background: g.color }} />
                {g.name}
              </div>
            ))}
          </div>
        </div>

        {/* ── Bar chart – file sizes ── */}
        <div className="bg-card border border-border rounded-2xl p-5 shadow-card">
          <p className="text-sm font-semibold text-foreground mb-1">File Sizes</p>
          <p className="text-xs text-muted-foreground mb-4">Storage used per file (MB)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sizeData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }} barSize={14}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ fill: "var(--accent)", radius: 6 }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="bg-card border border-border rounded-xl px-3 py-2 shadow-lg text-xs">
                      <p className="font-semibold text-foreground">{payload[0].payload.name}</p>
                      <p className="text-muted-foreground">{payload[0].value} MB</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="size" radius={[6, 6, 0, 0]}>
                {sizeData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── Radial bar – chunks ── */}
        <div className="bg-card border border-border rounded-2xl p-5 shadow-card">
          <p className="text-sm font-semibold text-foreground mb-1">Chunks Processed</p>
          <p className="text-xs text-muted-foreground mb-4">Vector chunks per document</p>
          <ResponsiveContainer width="100%" height={200}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="20%"
              outerRadius="90%"
              barSize={10}
              data={radialData}
              startAngle={180}
              endAngle={-180}
            >
              <RadialBar
                background={{ fill: "var(--accent)" }}
                dataKey="chunks"
                cornerRadius={6}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="bg-card border border-border rounded-xl px-3 py-2 shadow-lg text-xs">
                      <p className="font-semibold text-foreground">{payload[0].payload.name}</p>
                      <p className="text-muted-foreground">{payload[0].value} chunks</p>
                    </div>
                  );
                }}
              />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="flex flex-col gap-1 mt-2">
            {radialData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.fill }} />
                  <span className="text-muted-foreground truncate max-w-[100px]">{d.name}</span>
                </div>
                <span className="text-foreground font-medium">{d.chunks}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

// ── MAIN PAGE ─────────────────────────────────────────────────────────────────
const DocumentsPage = () => {
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "list">("grid");
  const [filter, setFilter] = useState<FilterType>("all");
  const [showAnalytics, setShowAnalytics] = useState(true);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        setError(null);
        const status = await api.getStatus();

        if (isMounted) {
          setSystemStatus(status);
        }

        const documentsResponse = await api.getDocuments();
        console.log("[DocumentsPage] getDocuments response:", documentsResponse);

        if (isMounted) {
          setDocuments(normalizeDocumentsResponse(documentsResponse));
        }
      } catch (error) {
        console.error("Failed to fetch status or documents:", error);
        if (isMounted) {
          setDocuments([]);
          setError("Failed to load documents.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  const counts = useMemo(() => ({
    all:   documents.length,
    video: documents.filter((d) => d.type === "video").length,
    audio: documents.filter((d) => d.type === "audio").length,
    image: documents.filter((d) => d.type === "image").length,
    text:  documents.filter((d) => isTextFile(d.type)).length,
  }), [documents]);

  const filtered = useMemo(() =>
    documents.filter((d) => {
      const matchSearch = d.name.toLowerCase().includes(search.toLowerCase());
      const matchFilter =
        filter === "all"   ? true :
        filter === "video" ? d.type === "video" :
        filter === "audio" ? d.type === "audio" :
        filter === "image" ? d.type === "image" :
        isTextFile(d.type);
      return matchSearch && matchFilter;
    }), [documents, search, filter]);

  const handleOpenDocument = (doc: Document) =>
    alert(`Opening ${doc.name} — This would take you to the document viewer`);

  const handleDownloadDocument = (doc: Document) =>
    alert(`Downloading ${doc.name} — This would download the file`);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
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
          {/* Analytics toggle */}
          <button
            onClick={() => setShowAnalytics((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors ${
              showAnalytics
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Analytics
          </button>

          <button
            onClick={() => setView("grid")}
            className={`p-2 rounded-lg transition-colors ${
              view === "grid" ? "bg-accent text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Grid3X3 className="w-5 h-5" />
          </button>
          <button
            onClick={() => setView("list")}
            className={`p-2 rounded-lg transition-colors ${
              view === "list" ? "bg-accent text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* ── Analytics Section ── */}
      {showAnalytics && <AnalyticsSection documents={documents} />}

      {/* Divider */}
      {showAnalytics && <div className="border-t border-border" />}

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
          { key: "all",   label: `All (${counts.all})` },
          { key: "video", label: `Video (${counts.video})` },
          { key: "text",  label: `Text files (${counts.text})` },
          { key: "image", label: `Images (${counts.image})` },
          { key: "audio", label: `Voice (${counts.audio})` },
        ].map((item) => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key as FilterType)}
            className={`px-4 py-1.5 rounded-full text-sm border transition ${
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
            const meta = getTypeMeta(doc.type);
            return (
              <div
                key={doc.id}
                className="bg-card border border-border rounded-2xl p-5 shadow-card hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5 group"
                style={{ borderTop: `2px solid ${meta.color}` }}
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: `${meta.color}18` }}>
                  <Icon className="w-6 h-6" style={{ color: meta.color }} />
                </div>

                <h3 className="text-sm font-medium text-foreground truncate mb-1" title={doc.name}>
                  {doc.name}
                </h3>
                <p className="text-xs text-muted-foreground mb-2">
                  {doc.size} · {doc.uploadedAt}
                </p>
                {doc.chunks && (
                  <p className="text-xs text-muted-foreground mb-4">
                    {doc.chunks} chunks processed
                  </p>
                )}

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
            const meta = getTypeMeta(doc.type);
            return (
              <div
                key={doc.id}
                className="flex items-center gap-4 p-4 bg-card border border-border rounded-xl shadow-card hover:shadow-card-hover transition-all duration-200 group"
              >
                <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: `${meta.color}18` }}>
                  <Icon className="w-5 h-5" style={{ color: meta.color }} />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{doc.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {doc.size} · {doc.uploadedAt}
                    {doc.chunks && ` · ${doc.chunks} chunks`}
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

      {filtered.length === 0 && (
        <div className="text-center py-12">
          <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">{error ?? "No documents found"}</p>
        </div>
      )}
    </div>
  );
};

export default DocumentsPage;