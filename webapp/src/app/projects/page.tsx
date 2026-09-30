"use client";

import { useTelegramUser } from "@/lib/twa";
import { Zap, Plus, AlertCircle, ChevronRight, Settings2 } from "lucide-react";

export default function Projects() {
  const { user } = useTelegramUser();

  // Mock data for projects
  const projects = [
    { id: 1, name: "Main Channel Updates", target: "@univora_updates", status: "active", buttons: 2 },
    { id: 2, name: "Movie Links Forwarder", target: "-10049281231", status: "paused", buttons: 4 },
  ];

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
        <button className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 w-full md:w-auto">
          <Plus className="w-5 h-5" />
          New Project
        </button>
      </header>

      {/* Projects Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {projects.map((proj) => (
          <div key={proj.id} className="glass-card rounded-3xl p-6 flex flex-col group hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
            <div className="flex items-start justify-between mb-4">
              <div className="p-3 bg-secondary rounded-2xl text-foreground">
                <Zap className="w-6 h-6" />
              </div>
              <span className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full ${
                proj.status === 'active' 
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' 
                  : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
              }`}>
                {proj.status}
              </span>
            </div>
            
            <h3 className="text-lg font-bold text-foreground mb-1 group-hover:text-primary transition-colors">{proj.name}</h3>
            <p className="text-sm font-mono text-muted-foreground mb-6">{proj.target}</p>
            
            <div className="mt-auto pt-4 border-t border-border/50 flex items-center justify-between">
              <div className="text-sm font-medium text-muted-foreground">
                <span className="text-foreground font-bold">{proj.buttons}</span> Buttons
              </div>
              <button className="p-2 bg-background rounded-xl hover:bg-secondary transition-colors">
                <Settings2 className="w-5 h-5 text-foreground" />
              </button>
            </div>
          </div>
        ))}
        
        {/* Create New Card */}
        <button className="glass-card rounded-3xl p-6 flex flex-col items-center justify-center gap-4 text-muted-foreground hover:text-foreground hover:border-primary/50 hover:bg-secondary/20 transition-all min-h-[220px] group border-dashed border-2">
          <div className="w-14 h-14 rounded-full bg-secondary flex items-center justify-center group-hover:scale-110 transition-transform duration-300 group-hover:bg-primary group-hover:text-primary-foreground">
            <Plus className="w-6 h-6" />
          </div>
          <span className="font-bold tracking-wide">Create Auto Adder</span>
        </button>
      </div>

      {/* Info Section */}
      <div className="rounded-3xl p-6 bg-secondary/30 border border-border/50 flex flex-col md:flex-row gap-4 items-start md:items-center text-sm text-muted-foreground">
        <AlertCircle className="w-6 h-6 text-primary shrink-0" />
        <p>
          <strong className="text-foreground">Pro tip:</strong> Auto Adders require the bot to be an Admin in your channel with <code className="px-1.5 py-0.5 rounded-md bg-background border border-border">Edit Messages</code> permission.
        </p>
      </div>
    </div>
  );
}
