"use client";

import { useState } from "react";
import { useTelegramUser } from "@/lib/twa";
import { Send, Image as ImageIcon, Video, FileText, CheckCircle2 } from "lucide-react";

export default function CreatePost() {
  const { user } = useTelegramUser();
  const [title, setTitle] = useState("");
  const [type, setType] = useState("text");
  const [content, setContent] = useState("");
  const [caption, setCaption] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      alert("Telegram authentication required.");
      return;
    }
    setLoading(true);

    try {
      let finalContent = content;

      if (type !== "text" && file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("type", type);
        
        const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
        const uploadData = await uploadRes.json();
        if (uploadData.error) throw new Error(uploadData.error);
        
        finalContent = uploadData.fileId;
      }

      const res = await fetch("/api/post/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: user.id,
          title,
          contentType: type,
          content: finalContent,
          caption: type !== "text" ? caption : "",
          buttons: []
        })
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setSuccess(true);
      setTitle("");
      setContent("");
      setCaption("");
      setFile(null);
      setTimeout(() => setSuccess(false), 5000);
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const types = [
    { id: "text", label: "Text", icon: FileText },
    { id: "photo", label: "Photo", icon: ImageIcon },
    { id: "video", label: "Video", icon: Video },
    { id: "document", label: "File", icon: FileText },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">Create Post</h1>
        <p className="text-muted-foreground text-lg">
          Craft a beautiful interactive message.
        </p>
      </header>

      {success && (
        <div className="p-4 flex items-center gap-3 text-sm font-medium text-primary-foreground rounded-2xl bg-primary border border-primary/20 shadow-lg animate-in slide-in-from-top-2">
          <CheckCircle2 className="w-5 h-5" />
          Post created successfully! Open Telegram to preview it.
        </div>
      )}

      <form onSubmit={handleSubmit} className="glass-card rounded-3xl p-6 md:p-8 space-y-8">
        
        {/* Type Selection */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">Media Type</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {types.map((t) => {
              const Icon = t.icon;
              const isSelected = type === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => { setType(t.id); setFile(null); setContent(""); }}
                  className={`flex flex-col items-center justify-center p-4 gap-2 rounded-2xl border transition-all duration-200 ${
                    isSelected 
                      ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/20 scale-[1.02]" 
                      : "bg-transparent text-muted-foreground border-border hover:border-primary/50 hover:bg-secondary/50"
                  }`}
                >
                  <Icon className="w-6 h-6" />
                  <span className="font-medium">{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Title */}
        <div className="space-y-3">
          <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">Internal Title</label>
          <input 
            type="text" 
            value={title} 
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-2xl border border-input bg-background/50 px-5 py-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            placeholder="E.g., Summer Sale Announcement"
          />
        </div>

        {/* Dynamic Content Field */}
        <div className="space-y-3 animate-in fade-in">
          {type === "text" ? (
            <>
              <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">Message Content</label>
              <textarea 
                value={content} 
                onChange={(e) => setContent(e.target.value)}
                required
                rows={6}
                className="w-full rounded-2xl border border-input bg-background/50 px-5 py-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                placeholder="Write your message here... (HTML supported)"
              />
            </>
          ) : (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-foreground uppercase tracking-wider mb-3">Upload File</label>
                <div className="border-2 border-dashed border-border rounded-3xl p-8 text-center hover:bg-secondary/20 transition-colors">
                  <input 
                    type="file" 
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    required
                    className="block w-full text-sm text-muted-foreground file:mr-4 file:py-3 file:px-6 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90 file:transition-colors file:cursor-pointer"
                  />
                  <p className="text-xs text-muted-foreground mt-4">Max size: 20MB. For larger files, send directly to the bot.</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-foreground uppercase tracking-wider mb-3">Caption</label>
                <textarea 
                  value={caption} 
                  onChange={(e) => setCaption(e.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-input bg-background/50 px-5 py-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                  placeholder="Add a caption... (HTML supported)"
                />
              </div>
            </div>
          )}
        </div>

        <div className="pt-6">
          <button 
            type="submit" 
            disabled={loading}
            className="w-full md:w-auto inline-flex justify-center items-center gap-2 rounded-full bg-primary px-8 py-4 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:hover:scale-100"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4" />
                Publish Post
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
