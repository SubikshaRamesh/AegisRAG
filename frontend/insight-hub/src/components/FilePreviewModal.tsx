import { X, Download, FileText, ExternalLink } from "lucide-react";

interface FilePreviewModalProps {
  isOpen: boolean;
  filename: string;
  onClose: () => void;
}

const getFileExtension = (filename: string): string =>
  filename.split(".").pop()?.toLowerCase() || "";

const TYPE_COLORS: Record<string, string> = {
  pdf: "#fb923c", mp4: "#38bdf8", webm: "#38bdf8", mov: "#38bdf8", avi: "#38bdf8", mkv: "#38bdf8",
  mp3: "#f472b6", wav: "#f472b6", ogg: "#f472b6", m4a: "#f472b6", aac: "#f472b6", flac: "#f472b6",
  jpg: "#34d399", jpeg: "#34d399", png: "#34d399", gif: "#34d399", webp: "#34d399", svg: "#34d399",
};
const getColor = (ext: string) => TYPE_COLORS[ext] ?? "#a78bfa";

export const FilePreviewModal = ({
  isOpen,
  filename,
  onClose,
}: FilePreviewModalProps) => {
  if (!isOpen) return null;

  const ext = getFileExtension(filename);
  const color = getColor(ext);
  const apiPath = `/api/files/${encodeURIComponent(filename)}?inline=true`;

  const renderPreview = () => {
    /* ---------- PDF ---------- */
    if (ext === "pdf") {
      return (
        <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", gap: 0 }}>
          {/* Try object tag first — much better PDF rendering than iframe */}
          <object
            data={apiPath}
            type="application/pdf"
            style={{ width: "100%", flex: 1, borderRadius: 12, border: "1px solid rgba(255,255,255,0.07)", background: "#1e1e2e" }}
          >
            {/* Fallback if object tag doesn't work */}
            <iframe
              src={`${apiPath}#toolbar=1&navpanes=1&scrollbar=1&view=FitH`}
              title={filename}
              style={{ width: "100%", height: "100%", border: "none", borderRadius: 12, background: "#1e1e2e" }}
            >
              {/* Last fallback */}
              <div style={{
                display: "flex", flexDirection: "column", alignItems: "center",
                justifyContent: "center", gap: 16, padding: 40, textAlign: "center"
              }}>
                <div style={{
                  width: 64, height: 64, borderRadius: "50%",
                  background: "rgba(251,146,60,0.1)", border: "1px solid rgba(251,146,60,0.3)",
                  display: "flex", alignItems: "center", justifyContent: "center"
                }}>
                  <FileText size={28} color="#fb923c" />
                </div>
                <div>
                  <p style={{ fontSize: 15, fontWeight: 600, color: "#e2e8f0", marginBottom: 6 }}>
                    PDF preview unavailable
                  </p>
                  <p style={{ fontSize: 13, color: "#64748b" }}>
                    Your browser doesn't support inline PDF previews.
                  </p>
                </div>
                <a
                  href={apiPath}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "8px 18px", borderRadius: 8, background: "rgba(251,146,60,0.15)",
                    border: "1px solid rgba(251,146,60,0.4)", color: "#fb923c",
                    fontSize: 13, fontWeight: 600, textDecoration: "none", fontFamily: "'DM Mono', monospace"
                  }}
                >
                  <ExternalLink size={14} />
                  Open in new tab
                </a>
              </div>
            </iframe>
          </object>
        </div>
      );
    }

    /* ---------- Images ---------- */
    if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(ext)) {
      return (
        <img
          src={apiPath}
          alt={filename}
          style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", borderRadius: 12 }}
        />
      );
    }

    /* ---------- Audio ---------- */
    if (["mp3", "wav", "aac", "flac", "ogg", "m4a"].includes(ext)) {
      return (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", gap: 24, padding: 40
        }}>
          <div style={{
            width: 100, height: 100, borderRadius: "50%",
            background: "rgba(244,114,182,0.1)", border: "1px solid rgba(244,114,182,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 40px rgba(244,114,182,0.15)"
          }}>
            <svg className="w-12 h-12" style={{ width: 48, height: 48, color: "#f472b6" }} fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
            </svg>
          </div>
          <audio controls src={apiPath} style={{ width: "100%", maxWidth: 420 }} />
          <p style={{ fontSize: 13, color: "#64748b", fontFamily: "'DM Mono', monospace" }}>{filename}</p>
        </div>
      );
    }

    /* ---------- Video ---------- */
    if (["mp4", "webm", "avi", "mov", "mkv"].includes(ext)) {
      return (
        <video
          controls
          src={apiPath}
          style={{ width: "100%", height: "100%", borderRadius: 12, objectFit: "contain", background: "#000" }}
        />
      );
    }

    /* ---------- Unsupported ---------- */
    return (
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", gap: 20, padding: 48, textAlign: "center"
      }}>
        <div style={{
          width: 80, height: 80, borderRadius: "50%",
          background: `rgba(167,139,250,0.1)`, border: "1px solid rgba(167,139,250,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center"
        }}>
          <FileText size={32} color="#a78bfa" />
        </div>
        <div>
          <p style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 }}>
            Preview not supported
          </p>
          <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6 }}>
            This file type cannot be previewed in the browser.<br />
            Download it to view locally.
          </p>
        </div>
        <a
          href={apiPath}
          download
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "9px 20px", borderRadius: 10, background: "rgba(167,139,250,0.15)",
            border: "1px solid rgba(167,139,250,0.4)", color: "#a78bfa",
            fontSize: 13, fontWeight: 600, textDecoration: "none", fontFamily: "'DM Mono', monospace"
          }}
        >
          <Download size={14} />
          Download {ext.toUpperCase()}
        </a>
      </div>
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.75)",
          backdropFilter: "blur(8px)",
          zIndex: 40,
        }}
      />

      {/* Modal */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 50,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 20, pointerEvents: "none"
      }}>
        <div style={{
          background: "rgba(15,18,30,0.98)",
          border: `1px solid ${color}22`,
          borderRadius: 20,
          boxShadow: `0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04), 0 0 60px ${color}11`,
          width: "100%",
          maxWidth: 960,
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          pointerEvents: "all",
          animation: "modalIn 0.22s cubic-bezier(.34,1.56,.64,1)",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "14px 18px",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            background: "rgba(255,255,255,0.02)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              <div style={{
                width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                background: `rgba(${color === "#fb923c" ? "251,146,60" : "56,189,248"},0.12)`,
                border: `1px solid ${color}33`,
                display: "flex", alignItems: "center", justifyContent: "center"
              }}>
                <FileText size={14} color={color} />
              </div>
              <span style={{
                fontSize: 14, fontWeight: 600, color: "#e2e8f0",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontFamily: "'DM Sans', sans-serif"
              }}>{filename}</span>
              <span style={{
                fontSize: 10, padding: "2px 7px", borderRadius: 4,
                background: `${color}18`, color, border: `1px solid ${color}33`,
                fontFamily: "'DM Mono', monospace", textTransform: "uppercase", flexShrink: 0
              }}>{ext}</span>
            </div>

            <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
              <a
                href={apiPath}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex", alignItems: "center", gap: 5, padding: "6px 12px",
                  borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
                  background: "rgba(255,255,255,0.04)", color: "#94a3b8",
                  fontSize: 12, textDecoration: "none", fontWeight: 600,
                  fontFamily: "'DM Mono', monospace"
                }}
              >
                <ExternalLink size={12} /> Open
              </a>
              <a
                href={apiPath}
                download
                style={{
                  display: "flex", alignItems: "center", gap: 5, padding: "6px 12px",
                  borderRadius: 8, border: `1px solid ${color}44`,
                  background: `${color}12`, color,
                  fontSize: 12, textDecoration: "none", fontWeight: 600,
                  fontFamily: "'DM Mono', monospace"
                }}
              >
                <Download size={12} /> Download
              </a>
              <button
                onClick={onClose}
                style={{
                  width: 30, height: 30, borderRadius: 8, border: "none",
                  background: "rgba(255,255,255,0.06)", color: "#94a3b8",
                  cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.2s"
                }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.12)")}
                onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* Content */}
          <div style={{
            flex: 1, overflow: "auto", padding: 16,
            display: "flex", alignItems: "center", justifyContent: "center",
            minHeight: 0,
          }}>
            {renderPreview()}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes modalIn {
          from { opacity: 0; transform: scale(0.95) translateY(8px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </>
  );
};