import { Link } from 'react-router-dom';
import { Button } from './ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import { MessageSquare, Shield, BookOpen, Sparkles, Zap, Lock } from 'lucide-react';

export function Home() {
  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center space-y-4 py-12">
        <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
          Welcome to QuietStories
        </h1>
        <p className="mx-auto max-w-[700px] text-lg text-muted-foreground sm:text-xl">
          Experience dynamic, AI-powered interactive storytelling. Create scenarios, explore
          narratives, and dive into worlds limited only by your imagination.
        </p>
        <div className="flex flex-wrap gap-4 justify-center pt-4">
          <Link to="/chat">
            <Button size="lg" className="gap-2">
              <MessageSquare className="h-5 w-5" />
              Start Chatting
            </Button>
          </Link>
          <Link to="/admin">
            <Button size="lg" variant="outline" className="gap-2">
              <Shield className="h-5 w-5" />
              Admin Panel
            </Button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <BookOpen className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Dynamic Scenarios</CardTitle>
            <CardDescription>
              Generate unique story scenarios from simple text descriptions using AI
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No pre-written scripts. Every story is dynamically created based on your input,
              making each playthrough unique.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Sparkles className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Interactive Storytelling</CardTitle>
            <CardDescription>
              Make choices that truly matter and shape your narrative
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Your actions have consequences. The AI adapts the story based on your decisions,
              creating a personalized experience.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Zap className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Real-time Processing</CardTitle>
            <CardDescription>
              Powered by FastAPI for lightning-fast responses
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Experience smooth, real-time interactions with the AI narrative engine, backed by
              a robust Python backend.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Lock className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Memory Management</CardTitle>
            <CardDescription>
              Private and public memory systems for realistic characters
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Characters maintain private thoughts and public actions, creating more believable
              and complex interactions.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Shield className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Admin Dashboard</CardTitle>
            <CardDescription>
              Monitor and manage all aspects of your stories
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              View sessions, inspect game state, and explore character memories through an
              intuitive admin interface.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <MessageSquare className="h-10 w-10 mb-2 text-primary" />
            <CardTitle>Clean Chat Interface</CardTitle>
            <CardDescription>
              Simple and elegant way to interact with your stories
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              A beautiful, distraction-free chat interface that lets you focus on the story and
              your choices.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Getting Started */}
      <section className="rounded-lg border bg-card text-card-foreground shadow-sm p-8">
        <div className="space-y-4">
          <h2 className="text-3xl font-bold tracking-tight">Getting Started</h2>
          <div className="space-y-4 text-muted-foreground">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Create a Scenario</h3>
                <p className="text-sm">
                  Navigate to the Chat page and describe your story scenario. The AI will
                  generate a complete interactive experience.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Make Your Choices</h3>
                <p className="text-sm">
                  Type your actions and watch as the story unfolds. Each turn processes your
                  input and generates new narrative content.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-1">Monitor Progress</h3>
                <p className="text-sm">
                  Use the Admin Panel to view all sessions, inspect game state, and explore
                  character memories and story progression.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
