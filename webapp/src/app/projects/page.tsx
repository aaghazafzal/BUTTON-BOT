"use client";

import { useEffect, useState } from "react";
import { useTelegramUser } from "@/lib/twa";
import { Zap, Plus, AlertCircle, Settings2, Loader2, ArrowLeft, Save, Trash2, PauseCircle, PlayCircle, Eye, Share2, Link, ThumbsUp } from "lucide-react";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

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

export default function Projects() {
  const { user } = useTelegramUser();

  const { data, error, isLoading, mutate } = useSWR(
    user?.id ? `/api/projects?userId=${user.id}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );

  const projects = data?.projects || [];

  const [isEditing, setIsEditing] = useState(false);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  
  const [channelId, setChannelId] = useState("");
  const [channelTitle, setChannelTitle] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [buttons, setButtons] = useState<BotButton[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const startCreate = () => {
    setCurrentProjectId(null);
    setChannelId("");
    setChannelTitle("");
    setIsActive(true);
    setButtons([]);
    setIsEditing(true);
  };

  const startEdit = (proj: any) => {
    setCurrentProjectId(proj.id);
    setChannelId(proj.channel_id);
    setChannelTitle(proj.channel_title);
    setIsActive(proj.is_active);
    try {
      const parsed = JSON.parse(proj.buttons_json || "[]");
      setButtons(parsed.map((b: any) => ({...b, id: Math.random().toString(36).substr(2, 9)})));
    } catch(e) {
      setButtons([]);
    }
    setIsEditing(true);
  };

  const saveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSaving(true);
    try {
      const buttonsJson = JSON.stringify(
        buttons.map(b => ({
          row_num: b.row_num,
          order_num: b.order_num,
          button_type: b.button_type,
          text: b.text,
          url: b.url || null,
          color: b.color || 'default'
        }))
      );

      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: currentProjectId,
          userId: user.id,
          channelId,
          channelTitle,
          buttonsJson,
          isActive
        })
      });
      const resData = await res.json();
      if (resData.error) throw new Error(resData.error);
      
      await mutate();
      setIsEditing(false);
    } catch (err: any) {
      alert("Error saving project: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteProject = async () => {
    if (!user || !currentProjectId) return;
    if (!confirm("Are you sure you want to delete this Auto Adder?")) return;
    setIsDeleting(true);
    try {
      const res = await fetch("/api/projects", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId: currentProjectId, userId: user.id })
      });
      await mutate();
      setIsEditing(false);
    } catch (err) {
      alert("Failed to delete");
    } finally {
      setIsDeleting(false);
    }
  };

  const togglePauseFromGrid = async (proj: any) => {
    if (!user) return;
    try {
      await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: proj.id,
          userId: user.id,
          channelId: proj.channel_id,
          channelTitle: proj.channel_title,
          buttonsJson: proj.buttons_json,
          isActive: !proj.is_active
        })
      });
      mutate();
    } catch (e) {}
  };

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

  const rows = buttons.reduce((acc, btn) => {
    if (!acc[btn.row_num]) acc[btn.row_num] = [];
    acc[btn.row_num].push(btn);
    return acc;
  }, {} as Record<number, BotButton[]>);

  Object.keys(rows).forEach(r => rows[parseInt(r)].sort((a, b) => a.order_num - b.order_num));

  if (isEditing) {
    return (
      <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-300 pb-20">
        <header className="flex items-center justify-between border-b border-border/50 pb-6">
          <div className="flex items-center gap-4">
            <button onClick={() => setIsEditing(false)} className="p-3 bg-secondary rounded-2xl hover:bg-secondary/80 transition-colors">
              <ArrowLeft className="w-6 h-6 text-foreground" />
            </button>
            <div className="space-y-1">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
                {currentProjectId ? "Edit Auto Adder" : "New Auto Adder"}
              </h1>
              <p className="text-muted-foreground text-sm">Configure automatic buttons for a channel.</p>
            </div>
          </div>
          {currentProjectId && (
            <button onClick={deleteProject} disabled={isDeleting} className="p-3 bg-red-500/10 text-red-500 rounded-2xl hover:bg-red-500/20 transition-colors">
              {isDeleting ? <Loader2 className="w-6 h-6 animate-spin" /> : <Trash2 className="w-6 h-6" />}
            </button>
          )}
        </header>

        <form onSubmit={saveProject} className="space-y-8">
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" /> Channel Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">Channel Title</label>
                <input 
                  type="text" 
                  value={channelTitle} 
                  onChange={(e) => setChannelTitle(e.target.value)}
                  required
                  className="w-full rounded-2xl border border-input bg-background/50 px-5 py-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="E.g., My Awesome Channel"
                />
              </div>
              <div className="space-y-3">
                <label className="block text-sm font-semibold text-foreground uppercase tracking-wider">Channel ID</label>
                <input 
                  type="text" 
                  value={channelId} 
                  onChange={(e) => setChannelId(e.target.value)}
                  required
                  className="w-full rounded-2xl border border-input bg-background/50 px-5 py-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="E.g., -100123456789"
                />
                <p className="text-xs text-muted-foreground">Bot must be an admin in this channel.</p>
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-2xl border border-border/50">
              <div>
                <h3 className="font-bold text-foreground">Status</h3>
                <p className="text-sm text-muted-foreground">{isActive ? "Buttons will be added to new posts." : "Auto Adder is paused."}</p>
              </div>
              <button 
                type="button" 
                onClick={() => setIsActive(!isActive)}
                className={`px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-colors ${isActive ? 'bg-amber-500/10 text-amber-600 hover:bg-amber-500/20' : 'bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20'}`}
              >
                {isActive ? <><PauseCircle className="w-4 h-4"/> Pause</> : <><PlayCircle className="w-4 h-4"/> Resume</>}
              </button>
            </div>
          </div>

          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold tracking-tight text-foreground">Inline Buttons to Attach</h2>
              <button type="button" onClick={addRow} className="text-sm font-bold text-primary hover:text-primary/80 transition-colors flex items-center gap-1 bg-primary/10 px-3 py-1.5 rounded-lg">
                <Plus className="w-4 h-4" /> Add Row
              </button>
            </div>

            <div className="space-y-6">
              {Object.keys(rows).length === 0 ? (
                <div className="text-center p-8 border-2 border-dashed border-border rounded-2xl text-muted-foreground">
                  <p>No buttons configured.</p>
                  <button type="button" onClick={addRow} className="mt-4 px-4 py-2 bg-secondary rounded-xl text-foreground font-medium hover:bg-secondary/80 transition-colors">
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
                          <button type="button" onClick={() => addButtonToRow(rowNum)} className="p-1.5 text-primary bg-primary/10 hover:bg-primary/20 rounded-lg transition-colors">
                            <Plus className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {rowBtns.map((btn) => (
                          <div key={btn.id} className="flex flex-col md:flex-row flex-wrap gap-3 bg-background p-3 rounded-xl border border-border/50 shadow-sm relative pr-12 md:pr-14">
                            <select 
                              value={btn.button_type} 
                              onChange={(e) => updateButton(btn.id, { button_type: e.target.value as ButtonType, text: e.target.value === 'url' ? 'Link' : e.target.value })}
                              className="bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none md:w-[130px] focus:ring-2 focus:ring-primary/20 shrink-0"
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
                              <>
                                <input 
                                  type="url" 
                                  value={btn.url || ""} 
                                  onChange={(e) => updateButton(btn.id, { url: e.target.value })}
                                  placeholder="https://"
                                  className="flex-1 min-w-[150px] bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none focus:ring-2 focus:ring-primary/20"
                                />
                                <select 
                                  value={btn.color || 'default'} 
                                  onChange={(e) => updateButton(btn.id, { color: e.target.value })}
                                  className="bg-secondary text-foreground text-sm rounded-lg px-3 py-2 border-none outline-none w-full md:w-[110px] focus:ring-2 focus:ring-primary/20 shrink-0 relative z-10"
                                >
                                  <option value="default">Neutral</option>
                                  <option value="primary">Blue</option>
                                  <option value="success">Green</option>
                                  <option value="danger">Red</option>
                                </select>
                              </>
                            )}

                            <button type="button" onClick={() => removeButton(btn.id)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors flex items-center justify-center z-10">
                              <Trash2 className="w-5 h-5" />
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

          <button 
            type="submit" 
            disabled={isSaving}
            className="w-full inline-flex justify-center items-center gap-2 rounded-2xl bg-primary px-8 py-4 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:hover:scale-100"
          >
            {isSaving ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Save className="w-5 h-5" />
                {currentProjectId ? "Save Changes" : "Create Auto Adder"}
              </>
            )}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out pb-10">
      
      {/* Header Section */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-foreground">
            Auto Adders
          </h1>
          <p className="text-muted-foreground text-lg max-w-xl">
            Automatically attach buttons to every new post in your connected channels.
          </p>
        </div>
        <button onClick={startCreate} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 w-full md:w-auto">
          <Plus className="w-5 h-5" />
          New Project
        </button>
      </header>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : (
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((proj: any) => {
          let parsedButtons = [];
          try {
            parsedButtons = JSON.parse(proj.buttons_json || "[]");
          } catch(e) {}
          
          return (
          <div key={proj.id} className="glass-card rounded-3xl p-6 flex flex-col group hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
            <div className="flex items-start justify-between mb-4">
              <div className={`p-3 rounded-2xl text-foreground transition-colors ${proj.is_active ? 'bg-secondary' : 'bg-background border border-border/50'}`}>
                <Zap className="w-6 h-6" />
              </div>
              <button 
                onClick={() => togglePauseFromGrid(proj)}
                className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full transition-colors hover:scale-105 ${
                proj.is_active 
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20' 
                  : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
              }`}>
                {proj.is_active ? "active" : "paused"}
              </button>
            </div>
            
            <h3 className="text-lg font-bold text-foreground mb-1 group-hover:text-primary transition-colors truncate">{proj.channel_title}</h3>
            <p className="text-sm font-mono text-muted-foreground mb-6 truncate">{proj.channel_id}</p>
            
            <div className="mt-auto pt-4 border-t border-border/50 flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">
                <span className="text-foreground font-bold">{parsedButtons.length}</span> Buttons
              </div>
              <button onClick={() => startEdit(proj)} className="p-2 bg-background rounded-xl hover:bg-secondary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <Settings2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        )})}
        
        {/* Create New Card */}
        <button onClick={startCreate} className="glass-card rounded-3xl p-6 flex flex-col items-center justify-center gap-4 text-muted-foreground hover:text-foreground hover:border-primary/50 hover:bg-secondary/20 transition-all min-h-[220px] group border-dashed border-2">
          <div className="w-14 h-14 rounded-full bg-secondary flex items-center justify-center group-hover:scale-110 transition-transform duration-300 group-hover:bg-primary group-hover:text-primary-foreground">
            <Plus className="w-6 h-6" />
          </div>
          <span className="font-bold tracking-wide">Create Auto Adder</span>
        </button>
      </div>
      )}

      {/* Info Section */}
      <div className="rounded-3xl p-6 bg-secondary/30 border border-border/50 flex flex-col md:flex-row gap-4 items-start md:items-center text-sm text-muted-foreground mt-8">
        <AlertCircle className="w-6 h-6 text-primary shrink-0" />
        <p>
          <strong className="text-foreground">Pro tip:</strong> Auto Adders require the bot to be an Admin in your channel with <code className="px-1.5 py-0.5 rounded-md bg-background border border-border">Edit Messages</code> permission.
        </p>
      </div>
    </div>
  );
}
