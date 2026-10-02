"use client";

import { useState, useEffect } from "react";
import { useTelegramUser } from "@/lib/twa";
import { Send, Image as ImageIcon, Video, FileText, CheckCircle2, Plus, Trash2, Link, ThumbsUp, Eye, Share2, AlignJustify } from "lucide-react";

type ButtonType = "url" | "like" | "dislike" | "views" | "share";

interface BotButton {
  id: string;
  row_num: number;
  order_num: number;
  button_type: ButtonType;
  text: string;
  url?: string;
  color?: string;
}

export default function CreatePost() {
  const { user } = useTelegramUser();
  const [title, setTitle] = useState("");
  const [type, setType] = useState("text");
  const [content, setContent] = useState("");
  const [caption, setCaption] = useState("");
  const [file, setFile] = useState<File | null>(null);
  
  const [buttons, setButtons] = useState<BotButton[]>([]);
  const [mounted, setMounted] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

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
          buttons: buttons
        })
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setSuccess(true);
      setTitle("");
      setContent("");
      setCaption("");
      setFile(null);
      setButtons([]);
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

  // Button Builder Logic
  const addRow = () => {
    const nextRow = buttons.length > 0 ? Math.max(...buttons.map(b => b.row_num)) + 1 : 0;
    setButtons([...buttons, {
      id: Math.random().toString(36).substr(2, 9),
      row_num: nextRow,
      order_num: 0,
      button_type: "url",
      text: "New Button",
      url: "https://",
    }]);
  };

  const addButtonToRow = (row_num: number) => {
    const rowBtns = buttons.filter(b => b.row_num === row_num);
    const nextOrder = rowBtns.length > 0 ? Math.max(...rowBtns.map(b => b.order_num)) + 1 : 0;
    setButtons([...buttons, {
      id: Math.random().toString(36).substr(2, 9),
      row_num,
      order_num: nextOrder,
      button_type: "url",
      text: "New Button",
      url: "https://",
    }]);
  };

  const updateButton = (id: string, updates: Partial<BotButton>) => {
    setButtons(buttons.map(b => b.id === id ? { ...b, ...updates } : b));
  };

  const removeButton = (id: string) => {
    setButtons(buttons.filter(b => b.id !== id));
  };

  // Group buttons by row for rendering
  const rows = buttons.reduce((acc, btn) => {
    if (!acc[btn.row_num]) acc[btn.row_num] = [];
    acc[btn.row_num].push(btn);
    return acc;
  }, {} as Record<number, BotButton[]>);

  Object.keys(rows).forEach(r => rows[parseInt(r)].sort((a, b) => a.order_num - b.order_num));

  if (!mounted) return null;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out pb-20">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-foreground">Create Post</h1>
        <p className="text-muted-foreground text-lg">
          Craft a beautiful interactive message with inline buttons.
        </p>
      </header>

      {success && (
        <div className="p-4 flex items-center gap-3 text-sm font-medium text-primary-foreground rounded-2xl bg-primary border border-primary/20 shadow-lg animate-in slide-in-from-top-2">
          <CheckCircle2 className="w-5 h-5" />
          Post created successfully! Open Telegram to preview it.
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* LEFT COLUMN - FORM */}
        <div className="xl:col-span-7 space-y-6">
          <form id="post-form" onSubmit={handleSubmit} className="glass-card rounded-3xl p-6 md:p-8 space-y-8">
            
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
          </form>

          {/* BUTTON BUILDER SECTION */}
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                <AlignJustify className="w-5 h-5 text-primary" />
                Inline Buttons
              </h2>
              <button onClick={addRow} className="text-sm font-bold text-primary hover:text-primary/80 transition-colors flex items-center gap-1 bg-primary/10 px-3 py-1.5 rounded-lg">
                <Plus className="w-4 h-4" /> Add Row
              </button>
            </div>

            <div className="space-y-6">
              {Object.keys(rows).length === 0 ? (
                <div className="text-center p-8 border-2 border-dashed border-border rounded-2xl text-muted-foreground">
                  <p>No buttons added yet.</p>
                  <button onClick={addRow} className="mt-4 px-4 py-2 bg-secondary rounded-xl text-foreground font-medium hover:bg-secondary/80 transition-colors">
                    Add First Button
                  </button>
                </div>
              ) : (
                Object.entries(rows).map(([rowStr, rowBtns]) => {
                  const rowNum = parseInt(rowStr);
                  return (
                    <div key={rowNum} className="p-4 rounded-2xl bg-secondary/30 border border-border/50 space-y-4 relative group">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase text-muted-foreground tracking-wider bg-background px-2 py-1 rounded-md">Row {rowNum + 1}</span>
                        <div className="flex gap-2">
                          <button onClick={() => addButtonToRow(rowNum)} className="p-1.5 text-primary bg-primary/10 hover:bg-primary/20 rounded-lg transition-colors" title="Add Button to Row">
                            <Plus className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {rowBtns.map((btn) => (
                          <div key={btn.id} className="flex flex-col flex-wrap lg:flex-nowrap lg:flex-row gap-3 bg-background p-3 rounded-xl border border-border/50 shadow-sm relative">
                            
                            <select 
                              value={btn.button_type} 
                              onChange={(e) => updateButton(btn.id, { button_type: e.target.value as ButtonType, text: e.target.value === 'url' ? 'Link' : e.target.value })}
                              className="bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none lg:w-32 focus:ring-2 focus:ring-primary/20 shrink-0"
                            >
                              <option value="url">URL Link</option>
                              <option value="like">👍 Like</option>
                              <option value="dislike">👎 Dislike</option>
                              <option value="views">👁️ Views</option>
                              <option value="share">📤 Share</option>
                            </select>

                            <input 
                              type="text" 
                              value={btn.text} 
                              onChange={(e) => updateButton(btn.id, { text: e.target.value })}
                              placeholder="Button Text"
                              className="flex-1 min-w-[120px] bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none focus:ring-2 focus:ring-primary/20"
                            />

                            {btn.button_type === "url" && (
                              <div className="flex flex-1 flex-col sm:flex-row gap-2">
                                <input 
                                  type="url" 
                                  value={btn.url || ""} 
                                  onChange={(e) => updateButton(btn.id, { url: e.target.value })}
                                  placeholder="https://"
                                  className="flex-1 min-w-[120px] bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none focus:ring-2 focus:ring-primary/20"
                                />
                                <select 
                                  value={btn.color || 'default'} 
                                  onChange={(e) => updateButton(btn.id, { color: e.target.value })}
                                  className="bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none sm:w-28 focus:ring-2 focus:ring-primary/20 shrink-0"
                                >
                                  <option value="default">Neutral</option>
                                  <option value="primary">Blue</option>
                                  <option value="success">Green</option>
                                  <option value="danger">Red</option>
                                </select>
                              </div>
                            )}

                            <button onClick={() => removeButton(btn.id)} className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors shrink-0 flex items-center justify-center">
                              <Trash2 className="w-5 h-5 lg:w-4 lg:h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
          
          {/* Submit Button (Desktop Hidden, Mobile Visible) */}
          <div className="block xl:hidden">
            <button 
              form="post-form"
              type="submit" 
              disabled={loading}
              className="w-full inline-flex justify-center items-center gap-2 rounded-2xl bg-primary px-8 py-4 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:hover:scale-100"
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
        </div>

        {/* RIGHT COLUMN - LIVE PREVIEW */}
        <div className="xl:col-span-5 relative">
          <div className="sticky top-6 space-y-6">
            <h2 className="text-xl font-bold tracking-tight text-foreground px-2 flex items-center justify-between">
              Live Preview
              <span className="text-xs bg-primary/20 text-primary px-2 py-1 rounded-md uppercase tracking-wide">Real-time</span>
            </h2>
            
            <div className="glass-card rounded-3xl p-4 md:p-6 bg-[#0f172a]/40 dark:bg-[#0f172a]/60 border-border/30 shadow-2xl relative overflow-hidden flex flex-col min-h-[400px]">
              {/* Telegram Background Pattern */}
              <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'url("https://www.transparenttextures.com/patterns/cubes.png")' }}></div>
              
              {/* Chat Bubble */}
              <div className="relative z-10 w-full max-w-[90%] bg-background/80 backdrop-blur-md rounded-2xl rounded-tl-sm p-3 shadow-sm border border-border/40">
                {/* Media Placeholder */}
                {type !== "text" && (
                  <div className="w-full aspect-video bg-secondary/50 rounded-xl mb-3 flex items-center justify-center text-muted-foreground overflow-hidden">
                    {file && type === "photo" ? (
                      <img src={URL.createObjectURL(file)} className="w-full h-full object-cover" alt="Preview" />
                    ) : file && type === "video" ? (
                      <video src={URL.createObjectURL(file)} className="w-full h-full object-cover" />
                    ) : (
                      <ImageIcon className="w-8 h-8 opacity-50" />
                    )}
                  </div>
                )}
                
                {/* Text Content */}
                <div className="text-[15px] leading-relaxed text-foreground break-words whitespace-pre-wrap">
                  {(type === "text" ? content : caption) || <span className="text-muted-foreground italic">Message text will appear here...</span>}
                </div>
                
                {/* Time */}
                <div className="text-[11px] text-right text-muted-foreground/70 mt-1">
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>

              {/* Inline Buttons Preview */}
              <div className="relative z-10 w-full max-w-[90%] mt-1.5 space-y-1.5">
                {Object.entries(rows).map(([rowStr, rowBtns]) => (
                  <div key={rowStr} className="flex gap-1.5 w-full">
                    {rowBtns.map(btn => (
                      <div 
                        key={btn.id} 
                        className={`flex-1 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-1.5 py-2.5 px-1 sm:px-2 rounded-xl text-[12px] sm:text-[13px] font-medium transition-colors shadow-sm backdrop-blur-md border border-white/5
                          ${btn.button_type === 'url' && btn.color === 'primary' ? 'bg-primary/20 text-primary hover:bg-primary/30' :
                            btn.button_type === 'url' && btn.color === 'success' ? 'bg-emerald-500/20 text-emerald-500 dark:text-emerald-400 hover:bg-emerald-500/30' :
                            btn.button_type === 'url' && btn.color === 'danger' ? 'bg-red-500/20 text-red-600 dark:text-red-400 hover:bg-red-500/30' :
                            btn.button_type === 'views' || btn.button_type === 'share' ? 'bg-primary/20 text-primary hover:bg-primary/30' :
                            'bg-background/70 text-foreground hover:bg-background/90'}
                        `}
                      >
                        <div className="flex items-center gap-1.5">
                          {btn.button_type === 'url' && <Link className="w-3.5 h-3.5" />}
                          {btn.button_type === 'share' && <Share2 className="w-3.5 h-3.5" />}
                          {btn.button_type === 'views' && <Eye className="w-3.5 h-3.5" />}
                          {btn.button_type === 'like' && <ThumbsUp className="w-3.5 h-3.5" />}
                          {btn.button_type === 'dislike' && <ThumbsUp className="w-3.5 h-3.5 rotate-180" />}
                          
                          <span className="truncate max-w-[80px] sm:max-w-none">{btn.text}</span>
                        </div>
                        {(btn.button_type === 'like' || btn.button_type === 'dislike' || btn.button_type === 'views' || btn.button_type === 'share') && (
                          <span className="bg-foreground/10 px-1.5 py-0.5 rounded-md text-[10px] ml-0 sm:ml-1 mt-1 sm:mt-0">0</span>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Submit Button (Desktop Visible, Mobile Hidden) */}
            <div className="hidden xl:block pt-4">
              <button 
                form="post-form"
                type="submit" 
                disabled={loading}
                className="w-full inline-flex justify-center items-center gap-2 rounded-2xl bg-primary px-8 py-4 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:hover:scale-100"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Publish Post to Bot
                  </>
                )}
              </button>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}
