import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageSquare, Shield, Moon, Sun } from 'lucide-react';
import { Button } from './ui/Button';
import { useState, useEffect } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Check for saved theme preference or default to system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    
    setIsDark(shouldBeDark);
    if (shouldBeDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleTheme = () => {
    const newIsDark = !isDark;
    setIsDark(newIsDark);
    
    if (newIsDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b sticky top-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4 mx-auto max-w-7xl">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center space-x-2">
              <h1 className="text-xl font-bold">QuietStories</h1>
            </Link>
            <nav className="flex items-center space-x-2">
              <Link to="/chat">
                <Button
                  variant={isActive('/chat') ? 'default' : 'ghost'}
                  size="sm"
                  className="gap-2"
                >
                  <MessageSquare className="h-4 w-4" />
                  Chat
                </Button>
              </Link>
              <Link to="/admin">
                <Button
                  variant={isActive('/admin') ? 'default' : 'ghost'}
                  size="sm"
                  className="gap-2"
                >
                  <Shield className="h-4 w-4" />
                  Admin
                </Button>
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-7xl px-4 py-6">
        {children}
      </main>

      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row mx-auto max-w-7xl px-4">
          <p className="text-sm text-muted-foreground">
            QuietStories - Dynamic CYOA Engine
          </p>
          <p className="text-sm text-muted-foreground">
            Built with FastAPI & React
          </p>
        </div>
      </footer>
    </div>
  );
}

