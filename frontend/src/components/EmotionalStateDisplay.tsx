import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Badge } from './ui/Badge';
import { Heart, Smile, Frown, AlertTriangle, Zap, Shield, Eye, Clock } from 'lucide-react';
import type { Entity } from '../services/api';

interface RecentEmotion {
  emotion: string;
  intensity: number;
  turn: number;
}

interface EmotionalState {
  dominant_emotion: string;
  intensity: number;
  recent_emotions: RecentEmotion[];
  emotion_distribution: Record<string, { count: number; total_intensity: number }>;
}

interface EmotionalStateDisplayProps {
  sessionId: string;
  entities: Entity[];
  isVisible: boolean;
}

export function EmotionalStateDisplay({ sessionId, entities, isVisible }: EmotionalStateDisplayProps) {
  const [emotionalStates, setEmotionalStates] = useState<Record<string, EmotionalState>>({});
  const [isLoading, setIsLoading] = useState(false);

  const loadEmotionalStates = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      // For now, we'll simulate emotional state data since we don't have a backend endpoint yet
      // In a real implementation, this would call an API endpoint
      const mockEmotionalStates: Record<string, EmotionalState> = {};

      entities.forEach((entity) => {
        const emotions = ['joy', 'trust', 'anticipation', 'fear', 'sadness', 'anger'];
        const randomEmotion = emotions[Math.floor(Math.random() * emotions.length)];
        const intensity = Math.random() * 2 - 1; // -1 to 1

        const entityKey = entity.id || entity.name || 'unknown';
        mockEmotionalStates[entityKey] = {
          dominant_emotion: randomEmotion,
          intensity: intensity,
          recent_emotions: [
            { emotion: randomEmotion, intensity: intensity, turn: 1 },
            { emotion: emotions[Math.floor(Math.random() * emotions.length)], intensity: Math.random() * 2 - 1, turn: 0 }
          ],
          emotion_distribution: {
            [randomEmotion]: { count: 2, total_intensity: intensity * 2 }
          }
        };
      });

      setEmotionalStates(mockEmotionalStates);
    } catch (error) {
      console.error('Failed to load emotional states:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, entities]);

  useEffect(() => {
    if (isVisible && sessionId && entities.length > 0) {
      loadEmotionalStates();
    }
  }, [isVisible, sessionId, entities, loadEmotionalStates]);

  const getEntityName = (entityId: string) => {
    const entity = entities.find(e => e.id === entityId || e.name === entityId);
    return entity?.name || entityId;
  };

  const getEmotionIcon = (emotion: string) => {
    switch (emotion) {
      case 'joy': return <Smile className="h-4 w-4 text-yellow-500" />;
      case 'sadness': return <Frown className="h-4 w-4 text-blue-500" />;
      case 'anger': return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'fear': return <Shield className="h-4 w-4 text-purple-500" />;
      case 'trust': return <Heart className="h-4 w-4 text-green-500" />;
      case 'anticipation': return <Zap className="h-4 w-4 text-orange-500" />;
      case 'surprise': return <Eye className="h-4 w-4 text-cyan-500" />;
      case 'disgust': return <Frown className="h-4 w-4 text-green-600" />;
      default: return <Heart className="h-4 w-4 text-gray-500" />;
    }
  };

  const getEmotionColor = (emotion: string) => {
    switch (emotion) {
      case 'joy': return 'text-yellow-600 bg-yellow-100';
      case 'sadness': return 'text-blue-600 bg-blue-100';
      case 'anger': return 'text-red-600 bg-red-100';
      case 'fear': return 'text-purple-600 bg-purple-100';
      case 'trust': return 'text-green-600 bg-green-100';
      case 'anticipation': return 'text-orange-600 bg-orange-100';
      case 'surprise': return 'text-cyan-600 bg-cyan-100';
      case 'disgust': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getIntensityLabel = (intensity: number) => {
    if (intensity > 0.5) return 'Very Strong';
    if (intensity > 0.2) return 'Strong';
    if (intensity > -0.2) return 'Moderate';
    if (intensity > -0.5) return 'Weak';
    return 'Very Weak';
  };

  const getIntensityBar = (intensity: number) => {
    const percentage = Math.abs(intensity) * 100;
    const isPositive = intensity > 0;

    return (
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${isPositive ? 'bg-green-500' : 'bg-red-500'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  if (!isVisible) return null;

  return (
    <Card className="h-full">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Heart className="h-5 w-5" />
            Emotional States
          </CardTitle>
          <button
            onClick={loadEmotionalStates}
            disabled={isLoading}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {Object.keys(emotionalStates).length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <Heart className="h-12 w-12 text-gray-300 mb-4" />
            <p className="text-sm text-muted-foreground mb-2">
              No emotional data yet
            </p>
            <p className="text-xs text-muted-foreground">
              Emotional states will appear as characters experience events
            </p>
          </div>
        ) : (
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {Object.entries(emotionalStates).map(([entityId, state]) => (
              <div key={entityId} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getEmotionIcon(state.dominant_emotion)}
                    <span className="font-medium text-sm">
                      {getEntityName(entityId)}
                    </span>
                  </div>
                  <Badge className={getEmotionColor(state.dominant_emotion)}>
                    {state.dominant_emotion}
                  </Badge>
                </div>

                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Intensity</span>
                      <span className={state.intensity > 0 ? 'text-green-600' : 'text-red-600'}>
                        {state.intensity.toFixed(2)}
                      </span>
                    </div>
                    {getIntensityBar(state.intensity)}
                    <div className="text-xs text-muted-foreground mt-1">
                      {getIntensityLabel(state.intensity)}
                    </div>
                  </div>

                  {Object.keys(state.emotion_distribution).length > 1 && (
                    <div>
                      <div className="text-xs font-medium mb-1">Recent Emotions</div>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(state.emotion_distribution).map(([emotion, data]) => (
                          <Badge
                            key={emotion}
                            variant="outline"
                            className={`text-xs ${getEmotionColor(emotion)}`}
                          >
                            {emotion} ({data.count})
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {Object.keys(emotionalStates).length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated this turn
              </span>
              <span className="flex items-center gap-1">
                <Heart className="h-3 w-3" />
                {Object.keys(emotionalStates).length} characters tracked
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
