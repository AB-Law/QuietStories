import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import { Button } from './ui/Button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { apiService } from '../services/api';
import type { Session } from '../services/api';
import { Loader2, RefreshCw, Database, Users, BookOpen, Activity, PlayCircle } from 'lucide-react';

interface MemoryEntry {
  content: string;
  scope?: string;
  turn: number;
}

interface EntityMemory {
  entity_id: string;
  private_memory: MemoryEntry[];
  public_memory: MemoryEntry[];
}

export function AdminPanel() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [memories, setMemories] = useState<EntityMemory[]>([]);

  const loadSessions = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.listSessions();
      setSessions(response.sessions);
      if (response.sessions.length > 0 && !selectedSession) {
        const fullSession = await apiService.getSession(response.sessions[0].id);
        setSelectedSession(fullSession);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    setIsLoading(true);
    try {
      const session = await apiService.getSession(sessionId);
      setSelectedSession(session);

      // Fetch actual memories from backend
      try {
        const memoriesData = await apiService.getSessionMemories(sessionId);
        const convertedMemories = convertMemoriesToDisplay(memoriesData);
        setMemories(convertedMemories);
      } catch (error) {
        console.error('Failed to load memories:', error);
        setMemories([]);
      }
    } catch (error) {
      console.error('Failed to load session details:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const convertMemoriesToDisplay = (memoriesData: { private_memory: Record<string, MemoryEntry[]>, public_memory: Record<string, MemoryEntry[]> }): EntityMemory[] => {
    const entityMemoriesMap = new Map<string, EntityMemory>();

    // Process private memories
    Object.entries(memoriesData.private_memory).forEach(([entityId, memories]) => {
      if (!entityMemoriesMap.has(entityId)) {
        entityMemoriesMap.set(entityId, {
          entity_id: entityId,
          private_memory: [],
          public_memory: [],
        });
      }
      const entityMem = entityMemoriesMap.get(entityId)!;
      entityMem.private_memory = memories;
    });

    // Process public memories
    Object.entries(memoriesData.public_memory).forEach(([entityId, memories]) => {
      if (!entityMemoriesMap.has(entityId)) {
        entityMemoriesMap.set(entityId, {
          entity_id: entityId,
          private_memory: [],
          public_memory: [],
        });
      }
      const entityMem = entityMemoriesMap.get(entityId)!;
      entityMem.public_memory = memories;
    });

    return Array.from(entityMemoriesMap.values());
  };

  const resumeSession = (sessionId: string) => {
    // Navigate to chat with the session ID
    navigate('/chat', { state: { sessionId } });
  };

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const renderDynamicData = (data: any, depth = 0) => {
    if (data === null || data === undefined) {
      return <span className="text-muted-foreground italic">null</span>;
    }

    if (typeof data === 'string' || typeof data === 'number' || typeof data === 'boolean') {
      return <span className="text-foreground">{String(data)}</span>;
    }

    if (Array.isArray(data)) {
      return (
        <div className={`${depth > 0 ? 'ml-4 border-l-2 border-muted pl-3' : ''} space-y-1`}>
          {data.length === 0 ? (
            <span className="text-muted-foreground italic">Empty array</span>
          ) : (
            data.map((item, index) => (
              <div key={index} className="py-1">
                <span className="text-muted-foreground text-sm">[{index}]</span>{' '}
                {renderDynamicData(item, depth + 1)}
              </div>
            ))
          )}
        </div>
      );
    }

    if (typeof data === 'object') {
      return (
        <div className={`${depth > 0 ? 'ml-4 border-l-2 border-muted pl-3' : ''} space-y-2`}>
          {Object.keys(data).length === 0 ? (
            <span className="text-muted-foreground italic">Empty object</span>
          ) : (
            Object.entries(data).map(([key, value]) => (
              <div key={key} className="py-1">
                <span className="font-semibold text-primary">{key}:</span>{' '}
                {renderDynamicData(value, depth + 1)}
              </div>
            ))
          )}
        </div>
      );
    }

    return <span className="text-muted-foreground">Unknown type</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
          <p className="text-muted-foreground">
            Manage sessions and view dynamic memory data
          </p>
        </div>
        <Button onClick={loadSessions} disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sessions.length}</div>
            <p className="text-xs text-muted-foreground">Total sessions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Turn</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedSession?.turn || 0}</div>
            <p className="text-xs text-muted-foreground">Selected session</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Entries</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {memories.reduce(
                (acc, m) => acc + m.private_memory.length + m.public_memory.length,
                0
              )}
            </div>
            <p className="text-xs text-muted-foreground">Across all entities</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sessions</CardTitle>
            <CardDescription>Select a session to view details</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sessions.length === 0 ? (
                <p className="text-muted-foreground text-sm">No sessions available</p>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`rounded-lg border p-3 transition-colors ${
                      selectedSession?.id === session.id ? 'bg-accent' : ''
                    }`}
                  >
                    <div 
                      className="flex items-center justify-between cursor-pointer hover:opacity-80"
                      onClick={() => loadSessionDetails(session.id)}
                    >
                      <div className="flex-1">
                        <p className="font-medium text-sm truncate">{session.id}</p>
                        <p className="text-xs text-muted-foreground">
                          Scenario: {session.scenario_id}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">Turn {session.turn}</p>
                        <p className="text-xs text-muted-foreground">{session.status}</p>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t">
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => resumeSession(session.id)}
                      >
                        <PlayCircle className="mr-2 h-4 w-4" />
                        Resume Session
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session Details</CardTitle>
            <CardDescription>
              {selectedSession ? `ID: ${selectedSession.id}` : 'No session selected'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedSession ? (
              <p className="text-muted-foreground text-sm">Select a session to view details</p>
            ) : (
              <Tabs defaultValue="state" className="w-full">
                <TabsList className="w-full">
                  <TabsTrigger value="state" className="flex-1">
                    <Database className="mr-2 h-4 w-4" />
                    State
                  </TabsTrigger>
                  <TabsTrigger value="memories" className="flex-1">
                    <Users className="mr-2 h-4 w-4" />
                    Memories
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="state" className="space-y-4">
                  <div className="max-h-[400px] overflow-y-auto rounded-md border p-4">
                    {selectedSession.state && Object.keys(selectedSession.state).length > 0 ? (
                      renderDynamicData(selectedSession.state)
                    ) : (
                      <p className="text-muted-foreground text-sm italic">No state data available</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="memories" className="space-y-4">
                  <div className="max-h-[400px] overflow-y-auto space-y-4">
                    {memories.length === 0 ? (
                      <p className="text-muted-foreground text-sm italic">No memories available</p>
                    ) : (
                      memories.map((entityMemory) => (
                        <div key={entityMemory.entity_id} className="rounded-md border p-4">
                          <h3 className="font-semibold mb-2 flex items-center">
                            <Users className="mr-2 h-4 w-4" />
                            {entityMemory.entity_id}
                          </h3>

                          {entityMemory.public_memory.length > 0 && (
                            <div className="mb-3">
                              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                                Public Memory
                              </h4>
                              <div className="space-y-1">
                                {entityMemory.public_memory.map((memory, idx) => (
                                  <div key={idx} className="text-sm bg-muted/50 p-2 rounded">
                                    <p>{memory.content}</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      Turn {memory.turn}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {entityMemory.private_memory.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                                Private Memory
                              </h4>
                              <div className="space-y-1">
                                {entityMemory.private_memory.map((memory, idx) => (
                                  <div key={idx} className="text-sm bg-accent/50 p-2 rounded">
                                    <p>{memory.content}</p>
                                    <div className="flex justify-between items-center mt-1">
                                      <p className="text-xs text-muted-foreground">
                                        Turn {memory.turn}
                                      </p>
                                      {memory.scope && (
                                        <p className="text-xs text-muted-foreground">
                                          Scope: {memory.scope}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

