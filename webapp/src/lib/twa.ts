"use client";

import { useEffect, useState } from "react";

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

export function useTelegramUser() {
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Dynamically import the SDK only on the client side
    import("@twa-dev/sdk").then((module) => {
      const WebApp = module.default;
      if (typeof window !== "undefined") {
        WebApp.ready();
        WebApp.expand();
        if (WebApp.initDataUnsafe?.user) {
          setUser(WebApp.initDataUnsafe.user as TelegramUser);
        }
      }
      setIsLoading(false);
    }).catch(err => {
      console.error("Failed to load Telegram SDK", err);
      setIsLoading(false);
    });
  }, []);

  return { user, isLoading };
}
