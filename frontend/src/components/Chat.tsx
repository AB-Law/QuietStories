import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Button } from './ui/Button';
import { apiService } from '../services/api';
import type { Session, TurnResponse, Entity } from '../services/api';
import { Send, Loader2, Plus, Sparkles } from 'lucide-react';
import Settings from './Settings';
import { useUserSettings } from '../hooks/useLocalStorage';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  turnNumber?: number;
}

export function Chat() {
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [scenarioDescription, setScenarioDescription] = useState('');
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isEnrichingPrompt, setIsEnrichingPrompt] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [numCharacters, setNumCharacters] = useState(3);
  const [generateWorld, setGenerateWorld] = useState(true);
  const [generateEntityBackgrounds, setGenerateEntityBackgrounds] = useState(true);
  const { settings: localUserSettings } = useUserSettings();
  const [userSettings, setUserSettings] = useState<{ playerName: string; preferences: Record<string, any> }>({ playerName: '', preferences: {} });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load session if navigated from admin panel
  useEffect(() => {
    const state = location.state as { sessionId?: string };
    if (state?.sessionId && !currentSession) {
      loadExistingSession(state.sessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  // Sync user settings from localStorage
  useEffect(() => {
    setUserSettings({
      playerName: localUserSettings.playerName,
      preferences: localUserSettings.preferences
    });
  }, [localUserSettings]);

  const loadExistingSession = async (sessionId: string) => {
    setIsLoading(true);
    try {
      const session = await apiService.getSession(sessionId);
      setCurrentSession(session);

      // Load turn history as messages
      const historyMessages: Message[] = [];

      if (session.turn_history && session.turn_history.length > 0) {
        session.turn_history.forEach((turn) => {
          // Add user action message
          if (turn.user_action) {
            historyMessages.push({
              id: `turn-${turn.turn}-user`,
              role: 'user',
              content: turn.user_action,
              timestamp: new Date(turn.timestamp),
              turnNumber: turn.turn,
            });
          }

          // Add assistant narrative message
          historyMessages.push({
            id: `turn-${turn.turn}-assistant`,
            role: 'assistant',
            content: turn.narrative,
            timestamp: new Date(turn.timestamp),
            turnNumber: turn.turn,
          });
        });
      }

      // Add system message if there's history
      if (historyMessages.length > 0) {
        historyMessages.unshift({
          id: 'system-resumed',
          role: 'system',
          content: `Resumed session - Currently on Turn ${session.turn}`,
          timestamp: new Date(),
        });
      } else {
        historyMessages.push({
          id: 'system-start',
          role: 'system',
          content: `Session started - Turn ${session.turn}`,
          timestamp: new Date(),
        });
      }

      setMessages(historyMessages);
    } catch (error) {
      console.error('Failed to load session:', error);
      alert('Failed to load session. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const enrichPrompt = async () => {
    if (!scenarioDescription.trim()) {
      alert('Please enter a scenario description first');
      return;
    }

    if (scenarioDescription.length < 10) {
      alert('Please enter at least 10 characters');
      return;
    }

    setIsEnrichingPrompt(true);
    try {
      const response = await apiService.enrichPrompt(scenarioDescription);
      setScenarioDescription(response.enriched);
    } catch (error) {
      console.error('Failed to enrich prompt:', error);
      alert('Failed to enrich prompt. Please try again.');
    } finally {
      setIsEnrichingPrompt(false);
    }
  };

  const createNewSession = async () => {
    if (!scenarioDescription.trim()) {
      alert('Please enter a scenario description');
      return;
    }

    setIsCreatingSession(true);
    try {
      // Generate and compile scenario
      const scenario = await apiService.generateScenario(scenarioDescription);
      await apiService.compileScenario(scenario.id);

      // Create session with config
      const sessionResponse = await apiService.createSession({
        scenario_id: scenario.id,
        seed: Math.floor(Math.random() * 1000000),
        config: {
          num_characters: numCharacters,
          generate_world_background: generateWorld,
          generate_entity_backgrounds: generateEntityBackgrounds,
          player_name: userSettings.playerName || undefined,
          initial_entities: undefined,
          custom_state: undefined
        }
      });

      // Fetch full session data (includes world_background, entities, etc.)
      const fullSession = await apiService.getSession(sessionResponse.id);
      setCurrentSession(fullSession);

      // Create welcome message with world background
      const welcomeMessages: Message[] = [
        {
          id: '1',
          role: 'system',
          content: `Session created! Scenario: ${scenarioDescription}`,
          timestamp: new Date(),
        },
      ];

      // Add world background as a narrative message if available
      if (fullSession.world_background) {
        welcomeMessages.push({
          id: '2',
          role: 'assistant',
          content: fullSession.world_background,
          timestamp: new Date(),
          turnNumber: 0,
        });
      }

      setMessages(welcomeMessages);
      setScenarioDescription('');
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please try again.');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || !currentSession) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response: TurnResponse = await apiService.processTurn(currentSession.id, {
        action: inputValue,
        parameters: {},
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.outcome.narrative,
        timestamp: new Date(),
        turnNumber: response.turn,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Refresh full session data to get updated entities and turn history
      try {
        const updatedSession = await apiService.getSession(currentSession.id);
        console.log('Updated session entities:', updatedSession.entities?.length, 'entities');
        if (updatedSession.entities) {
          updatedSession.entities.forEach((e: Entity) => {
            console.log(`  - ${e.id || e.name}: background=${e.background ? 'YES' : 'NO'}`);
          });
        }
        setCurrentSession(updatedSession);
      } catch (error) {
        console.error('Failed to refresh session data:', error);
        // Fallback to just updating turn count
        setCurrentSession((prev) => (prev ? { ...prev, turn: response.turn } : null));
      }

      // Refocus input after message is sent
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: 'Failed to process your action. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (currentSession) {
        sendMessage();
      } else {
        createNewSession();
      }
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      {/* Main Chat Area */}
      <Card className={`flex-1 flex flex-col overflow-hidden ${showSidebar && currentSession ? 'lg:w-2/3' : 'w-full'}`}>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <CardTitle>
              {currentSession ? `Chat - Turn ${currentSession.turn || 0}` : 'Create New Session'}
            </CardTitle>
            <div className="flex gap-2">
              {currentSession && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSidebar(!showSidebar)}
                  >
                    {showSidebar ? 'Hide Info' : 'Show Info'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setCurrentSession(null);
                      setMessages([]);
                    }}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    New Session
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-y-auto p-6">
          {!currentSession ? (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
              <div className="max-w-md w-full space-y-4">
                <h2 className="text-2xl font-bold text-center">Start Your Story</h2>
                <p className="text-muted-foreground text-center">
                  Describe your scenario and let the AI create an interactive story for you.
                </p>
                <textarea
                  className="w-full min-h-[150px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="E.g., A detective investigating a mysterious disappearance in a small coastal town..."
                  value={scenarioDescription}
                  onChange={(e) => setScenarioDescription(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isEnrichingPrompt}
                />
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={enrichPrompt}
                    disabled={isEnrichingPrompt || !scenarioDescription.trim() || scenarioDescription.length < 10}
                  >
                    {isEnrichingPrompt ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Enriching...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Enrich Prompt
                      </>
                    )}
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={createNewSession}
                    disabled={isCreatingSession || isEnrichingPrompt || !scenarioDescription.trim()}
                  >
                    {isCreatingSession ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Create Session'
                    )}
                  </Button>
                </div>

                {/* Advanced Options */}
                <div className="border-t pt-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="w-full"
                  >
                    {showAdvanced ? '▼ Hide' : '▶ Show'} Advanced Options
                  </Button>

                  {showAdvanced && (
                    <div className="space-y-3 mt-3 p-4 border rounded-md bg-muted/20">
                      <div>
                        <label className="text-sm font-medium block mb-2">
                          Number of Characters to Generate
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="10"
                          value={numCharacters}
                          onChange={(e) => setNumCharacters(parseInt(e.target.value) || 3)}
                          className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          More characters = longer session creation time
                        </p>
                      </div>

                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="gen-world"
                          checked={generateWorld}
                          onChange={(e) => setGenerateWorld(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        <label htmlFor="gen-world" className="text-sm cursor-pointer">
                          Generate World Background
                        </label>
                      </div>

                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="gen-entities"
                          checked={generateEntityBackgrounds}
                          onChange={(e) => setGenerateEntityBackgrounds(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        <label htmlFor="gen-entities" className="text-sm cursor-pointer">
                          Generate Character Backgrounds
                        </label>
                      </div>

                      {/* Settings Component */}
                      <div className="border-t pt-3">
                        <Settings onSettingsChange={setUserSettings} />
                      </div>
                    </div>
                  )}
                </div>

                <p className="text-xs text-muted-foreground text-center">
                  💡 Tip: Use "Enrich Prompt" to let the AI expand your idea into a detailed scenario
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : message.role === 'system'
                        ? 'bg-muted text-muted-foreground italic'
                        : 'bg-secondary text-secondary-foreground'
                    }`}
                  >
                    {message.role === 'assistant' && message.turnNumber && (
                      <div className="text-xs opacity-70 mb-1">Turn {message.turnNumber}</div>
                    )}
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    <div className="text-xs opacity-70 mt-1">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-secondary text-secondary-foreground rounded-lg px-4 py-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </CardContent>

        {currentSession && (
          <div className="border-t p-4">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                placeholder="Type your action..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="flex-1 min-h-[40px] max-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none overflow-y-auto"
                rows={1}
                style={{ height: 'auto' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
              <Button onClick={sendMessage} disabled={isLoading || !inputValue.trim()}>
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Sidebar - World Info & Entities */}
      {currentSession && showSidebar && (
        <Card className="hidden lg:block lg:w-1/3 overflow-hidden flex flex-col">
          <CardHeader className="border-b">
            <CardTitle className="text-lg">World Info</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {currentSession.scenario_spec?.name ? (
              <div>
                <h3 className="font-semibold text-sm text-muted-foreground mb-1">Scenario</h3>
                <p className="text-sm">{currentSession.scenario_spec.name as string}</p>
              </div>
            ) : null}

            {/* Turn Counter */}
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground mb-1">Current Turn</h3>
              <p className="text-sm">{currentSession.turn}</p>
            </div>

            {/* World Background */}
            {currentSession.world_background && (
              <div>
                <h3 className="font-semibold text-sm text-muted-foreground mb-2">World Background</h3>
                <div className="text-sm bg-muted/50 rounded-md p-3 max-h-48 overflow-y-auto">
                  <p className="whitespace-pre-wrap">{currentSession.world_background}</p>
                </div>
              </div>
            )}

            {/* Entities/Characters */}
            {currentSession.entities && currentSession.entities.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm text-muted-foreground mb-2">
                  Characters ({currentSession.entities.length})
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {currentSession.entities.map((entity) => (
                    <div key={entity.id} className="bg-muted/30 rounded-md p-3 border">
                      <div className="flex items-start justify-between mb-1">
                        <h4 className="font-medium text-sm">
                          {entity.name || entity.id}
                        </h4>
                        <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
                          {entity.type}
                        </span>
                      </div>
                      {entity.background && (
                        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                          {entity.background}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Turn History Count */}
            {currentSession.turn_history && currentSession.turn_history.length > 0 && (
              <div>
                <h3 className="font-semibold text-sm text-muted-foreground mb-1">History</h3>
                <p className="text-sm">{currentSession.turn_history.length} turns recorded</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
