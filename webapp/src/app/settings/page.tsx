"use client";

import { useTelegramUser } from "@/lib/twa";
import { Shield, User, Crown, Activity, Bell, LogOut, ChevronRight, Loader2 } from "lucide-react";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Settings() {
  const { user } = useTelegramUser();

  const { data: stats, isLoading } = useSWR(
    user?.id ? `/api/stats?userId=${user.id}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );

  const isPremium = stats?.isPremiumActive || false;
  const isAdmin = stats?.isAdmin || false;
  const maxPosts = stats?.maxPosts || 100;
  const totalPosts = stats?.postCount || 0;
  
  // Calculate percentage, max at 100%
  const postPercentage = Math.min(100, Math.round((totalPosts / maxPosts) * 100)) || 0;

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out pb-10">
      
      {/* Header Section */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-foreground">
            Settings
          </h1>
          <p className="text-muted-foreground text-lg max-w-xl">
            Manage your account preferences, subscription limits, and application settings.
          </p>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-12">
        {/* Left Column: Profile & Plan */}
        <div className="space-y-6 md:col-span-5">
          {/* Profile Card */}
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <div className="flex items-center gap-5">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary border border-primary/20 shadow-inner overflow-hidden shrink-0">
                {user?.photo_url ? (
                  <img src={user.photo_url} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <User className="w-10 h-10" />
                )}
              </div>
              <div>
                <h2 className="text-2xl font-bold">{user ? `${user.first_name} ${user.last_name || ''}` : 'Loading...'}</h2>
                <p className="text-muted-foreground font-mono mt-1">{user ? `@${user.username || 'unknown'}` : ''}</p>
                <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary text-xs font-semibold">
                  <Activity className="w-3.5 h-3.5" /> ID: {user?.id || '---'}
                </div>
              </div>
            </div>
          </div>

          {/* Subscription Card */}
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6 relative overflow-hidden group">
            {isPremium && !isAdmin && (
              <div className="absolute -right-4 -top-4 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl group-hover:bg-amber-500/20 transition-colors"></div>
            )}
            {isAdmin && (
              <div className="absolute -right-4 -top-4 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-colors"></div>
            )}
            
            <div className="flex items-center gap-3 mb-2">
              <div className={`p-2.5 rounded-xl ${isAdmin ? 'bg-blue-500/20 text-blue-500' : isPremium ? 'bg-amber-500/20 text-amber-600 dark:text-amber-500' : 'bg-secondary text-foreground'}`}>
                {isAdmin ? <Shield className="w-6 h-6" /> : isPremium ? <Crown className="w-6 h-6" /> : <Shield className="w-6 h-6" />}
              </div>
              <h3 className="text-xl font-bold text-foreground">Current Plan</h3>
            </div>
            
            <div className="p-5 rounded-2xl bg-secondary/50 border border-border/50 relative">
              {isLoading && (
                <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-2xl">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              )}
              
              <div className="flex items-center justify-between mb-4">
                <span className="font-semibold text-foreground">{isAdmin ? "Admin Plan" : isPremium ? "Premium" : "Free Tier"}</span>
                {isAdmin ? (
                  <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-xs font-bold uppercase tracking-wider">
                    Infinity
                  </span>
                ) : isPremium ? (
                  <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-500 text-xs font-bold uppercase tracking-wider">
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider">
                    Basic
                  </span>
                )}
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Posts Sent</span>
                  <span className="font-medium">{totalPosts} / {maxPosts === 999999 ? "∞" : maxPosts}</span>
                </div>
                <div className="w-full h-2 bg-background rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-1000 ${isAdmin ? 'bg-blue-500' : isPremium ? 'bg-amber-500' : 'bg-primary'}`} 
                    style={{ width: `${isAdmin ? 100 : postPercentage}%` }}
                  ></div>
                </div>
              </div>
            </div>
            
            <button className="w-full py-3 rounded-xl bg-background border border-border hover:bg-secondary hover:border-primary/50 transition-colors font-bold text-sm">
              Upgrade Limits
            </button>
          </div>
        </div>

        {/* Right Column: Preferences */}
        <div className="space-y-6 md:col-span-7">
          <div className="glass-card rounded-3xl p-6 md:p-8">
            <h3 className="text-xl font-bold text-foreground mb-6">Preferences</h3>
            
            <div className="space-y-2">
              {[
                { icon: Bell, title: "Notifications", desc: "Get alerts when limits are reached" },
                { icon: Shield, title: "Privacy & Security", desc: "Manage connected sessions" },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-4 rounded-2xl hover:bg-secondary/50 transition-colors cursor-pointer border border-transparent hover:border-border/50">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-secondary rounded-xl text-foreground">
                      <item.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-sm">{item.title}</h4>
                      <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </div>
              ))}
            </div>
            
            <div className="mt-8 pt-6 border-t border-border/50">
              <button className="flex items-center gap-3 text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 transition-colors font-bold text-sm p-2">
                <LogOut className="w-5 h-5" />
                Disconnect Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
