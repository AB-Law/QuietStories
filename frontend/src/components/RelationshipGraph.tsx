import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { apiService } from '../services/api';
import { Network, Users, TrendingUp, Heart, Shield, Sword, BookOpen, Briefcase } from 'lucide-react';

interface RelationshipData {
  entity_a: string;
  entity_b: string;
  sentiment: number;
  relationship_type: string;
  memory_count: number;
  last_interaction: number;
}

interface RelationshipGraphProps {
  sessionId: string;
  entities: any[];
  isVisible: boolean;
}

export function RelationshipGraph({ sessionId, entities, isVisible }: RelationshipGraphProps) {
  const [relationships, setRelationships] = useState<Record<string, RelationshipData>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRelationship, setSelectedRelationship] = useState<string | null>(null);

  const loadRelationships = async () => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      const response = await apiService.getRelationships(sessionId);
      setRelationships(response.relationships || {});
    } catch (error) {
      console.error('Failed to load relationships:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isVisible && sessionId) {
      loadRelationships();
    }
  }, [isVisible, sessionId]);

  const getEntityName = (entityId: string) => {
    const entity = entities.find(e => e.id === entityId || e.name === entityId);
    return entity?.name || entityId;
  };

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-green-600';
    if (sentiment < -0.3) return 'text-red-600';
    return 'text-gray-600';
  };

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment > 0.5) return 'Very Positive';
    if (sentiment > 0.2) return 'Positive';
    if (sentiment > -0.2) return 'Neutral';
    if (sentiment > -0.5) return 'Negative';
    return 'Very Negative';
  };

  const getRelationshipIcon = (type: string) => {
    switch (type) {
      case 'romantic': return <Heart className="h-4 w-4 text-pink-500" />;
      case 'friendship': return <Users className="h-4 w-4 text-blue-500" />;
      case 'family': return <Heart className="h-4 w-4 text-purple-500" />;
      case 'mentor': return <BookOpen className="h-4 w-4 text-green-500" />;
      case 'professional': return <Briefcase className="h-4 w-4 text-gray-500" />;
      case 'adversarial': return <Sword className="h-4 w-4 text-red-500" />;
      default: return <Users className="h-4 w-4 text-gray-500" />;
    }
  };

  const getRelationshipBadgeColor = (type: string) => {
    switch (type) {
      case 'romantic': return 'bg-pink-100 text-pink-800';
      case 'friendship': return 'bg-blue-100 text-blue-800';
      case 'family': return 'bg-purple-100 text-purple-800';
      case 'mentor': return 'bg-green-100 text-green-800';
      case 'professional': return 'bg-gray-100 text-gray-800';
      case 'adversarial': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isVisible) return null;

  return (
    <Card className="h-full">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Network className="h-5 w-5" />
            Relationship Map
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={loadRelationships}
            disabled={isLoading}
          >
            {isLoading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {Object.keys(relationships).length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <Users className="h-12 w-12 text-gray-300 mb-4" />
            <p className="text-sm text-muted-foreground mb-2">
              No relationships found yet
            </p>
            <p className="text-xs text-muted-foreground">
              Relationships will appear as characters interact
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {Object.entries(relationships).map(([key, rel]) => (
              <div
                key={key}
                className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedRelationship === key
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-muted/50'
                }`}
                onClick={() => setSelectedRelationship(
                  selectedRelationship === key ? null : key
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getRelationshipIcon(rel.relationship_type)}
                    <span className="font-medium text-sm">
                      {getEntityName(rel.entity_a)} ↔ {getEntityName(rel.entity_b)}
                    </span>
                  </div>
                  <Badge className={getRelationshipBadgeColor(rel.relationship_type)}>
                    {rel.relationship_type}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div className="text-center">
                    <div className={`font-medium ${getSentimentColor(rel.sentiment)}`}>
                      {getSentimentLabel(rel.sentiment)}
                    </div>
                    <div className="text-muted-foreground">
                      {rel.sentiment.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Interactions</div>
                    <div className="text-muted-foreground">
                      {rel.memory_count}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">Last Seen</div>
                    <div className="text-muted-foreground">
                      Turn {rel.last_interaction}
                    </div>
                  </div>
                </div>

                {selectedRelationship === key && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="text-xs text-muted-foreground">
                      Click to collapse details
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {Object.keys(relationships).length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                {Object.keys(relationships).length} relationships
              </span>
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                {entities.length} characters
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
