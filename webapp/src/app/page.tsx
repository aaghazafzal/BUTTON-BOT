"use client";

import { useEffect, useState } from "react";
import { useTelegramUser } from "@/lib/twa";
import { Send, MousePointerClick, Zap, ArrowUpRight, Plus, Settings, History, ChevronRight } from "lucide-react";
import Link from "next/link";

export default function Home() {
  const { user, isLoading: authLoading } = useTelegramUser();
  const [stats, setStats] = useState({ postCount: 0, projectCount: 0, totalClicks: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.id) {
      fetch(`/api/stats?userId=${user.id}`)
        .then(res => res.json())
        .then(data => {
          setStats(data);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    } else if (!authLoading && !user) {
      // Mock for testing outside Telegram
      setStats({ postCount: 142, projectCount: 5, totalClicks: 8432 });
      setLoading(false);
    }
  }, [user, authLoading]);

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out pb-10">
      
      {/* Header Section */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-foreground">
            {user ? `Welcome back, ${user.first_name}` : 'Overview'}
          </h1>
          <p className="text-muted-foreground text-lg max-w-xl">
            Monitor your interactive posts, analyze engagement, and manage your Univora ecosystem.
          </p>
        </div>
        <Link 
          href="/create"
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-bold tracking-wide text-primary-foreground shadow-lg shadow-primary/20 hover:scale-[1.02] hover:shadow-primary/30 transition-all focus:outline-none focus:ring-2 focus:ring-primary/50 w-full md:w-auto"
        >
          <Plus className="w-5 h-5" />
          New Post
        </Link>
      </header>

      {/* Metrics Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Metric 1 */}
        <div className="glass-card rounded-3xl p-6 md:p-8 relative overflow-hidden group hover:shadow-xl hover:shadow-primary/5 transition-all duration-500 hover:-translate-y-1">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
            <Send className="w-32 h-32 rotate-12 translate-x-8 -translate-y-8 text-primary" />
          </div>
          <div className="flex flex-row items-center justify-between space-y-0 pb-6 relative z-10">
            <h3 className="tracking-widest text-xs font-bold text-muted-foreground uppercase">Total Posts</h3>
            <div className="p-3 bg-primary/10 rounded-2xl text-primary shadow-inner">
              <Send className="h-5 w-5" />
            </div>
          </div>
          <div className="text-5xl font-black tracking-tighter relative z-10 text-foreground">
            {loading ? "..." : stats.postCount.toLocaleString()}
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs font-bold text-primary/80">
            <ArrowUpRight className="w-4 h-4" />
            <span>+12% this month</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-card rounded-3xl p-6 md:p-8 relative overflow-hidden group hover:shadow-xl hover:shadow-primary/5 transition-all duration-500 hover:-translate-y-1">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
            <MousePointerClick className="w-32 h-32 rotate-12 translate-x-8 -translate-y-8 text-primary" />
          </div>
          <div className="flex flex-row items-center justify-between space-y-0 pb-6 relative z-10">
            <h3 className="tracking-widest text-xs font-bold text-muted-foreground uppercase">Button Clicks</h3>
            <div className="p-3 bg-primary/10 rounded-2xl text-primary shadow-inner">
              <MousePointerClick className="h-5 w-5" />
            </div>
          </div>
          <div className="text-5xl font-black tracking-tighter relative z-10 text-foreground">
            {loading ? "..." : stats.totalClicks.toLocaleString()}
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs font-bold text-primary/80">
            <ArrowUpRight className="w-4 h-4" />
            <span>+34% this month</span>
          </div>
        </div>
        
        {/* Metric 3 */}
        <div className="glass-card rounded-3xl p-6 md:p-8 relative overflow-hidden group hover:shadow-xl hover:shadow-primary/5 transition-all duration-500 hover:-translate-y-1">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
            <Zap className="w-32 h-32 rotate-12 translate-x-8 -translate-y-8 text-primary" />
          </div>
          <div className="flex flex-row items-center justify-between space-y-0 pb-6 relative z-10">
            <h3 className="tracking-widest text-xs font-bold text-muted-foreground uppercase">Auto Adders</h3>
            <div className="p-3 bg-primary/10 rounded-2xl text-primary shadow-inner">
              <Zap className="h-5 w-5" />
            </div>
          </div>
          <div className="text-5xl font-black tracking-tighter relative z-10 text-foreground">
            {loading ? "..." : stats.projectCount.toLocaleString()}
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs font-bold text-muted-foreground">
            <span>Active integrations</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout for wider screens */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Activity */}
        <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6 flex flex-col">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-secondary rounded-xl text-foreground">
                <History className="w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold text-foreground">Recent Activity</h2>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col gap-4">
            {[1, 2, 3].map((_, i) => (
              <div key={i} className="group flex items-center justify-between p-4 rounded-2xl bg-background/50 border border-border/50 hover:border-primary/30 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                    #{843 - i}
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors">Post successfully published</h4>
                    <p className="text-xs text-muted-foreground">Contains 3 interactive buttons</p>
                  </div>
                </div>
                <span className="text-xs font-medium text-muted-foreground">{i * 2 + 1}h ago</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions & Limits */}
        <div className="space-y-6">
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <h2 className="text-xl font-bold text-foreground mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-4">
              <Link href="/projects" className="flex flex-col items-start gap-4 p-5 rounded-2xl bg-secondary/30 hover:bg-secondary/70 border border-border/50 transition-all group">
                <div className="p-3 bg-background rounded-xl shadow-sm text-foreground group-hover:text-primary transition-colors">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm">Auto Adders</h4>
                  <p className="text-xs text-muted-foreground mt-1">Manage channels</p>
                </div>
              </Link>
              <Link href="/settings" className="flex flex-col items-start gap-4 p-5 rounded-2xl bg-secondary/30 hover:bg-secondary/70 border border-border/50 transition-all group">
                <div className="p-3 bg-background rounded-xl shadow-sm text-foreground group-hover:text-primary transition-colors">
                  <Settings className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm">Settings</h4>
                  <p className="text-xs text-muted-foreground mt-1">Plan & Limits</p>
                </div>
              </Link>
            </div>
          </div>
          
          {/* Plan Banner */}
          <div className="rounded-3xl p-6 md:p-8 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-xl relative overflow-hidden">
            <div className="relative z-10">
              <h3 className="text-lg font-bold mb-1">Premium Plan Active</h3>
              <p className="text-sm opacity-80 mb-4 max-w-[80%]">You have access to 200 posts and 40 buttons per post.</p>
              <button className="text-xs font-bold uppercase tracking-wider bg-background text-foreground px-4 py-2 rounded-xl hover:scale-105 transition-transform">
                View Details
              </button>
            </div>
            {/* Decorative background element */}
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-white opacity-10 rounded-full blur-2xl"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
