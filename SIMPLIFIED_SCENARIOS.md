# Simplified Scenario System

## Overview

The Simplified Scenario System is a new, narrative-driven approach to scenario creation that replaces the complex ScenarioSpec-based architecture. It focuses on world-building and character development rather than rigid rule systems.

## Key Differences

### Legacy ScenarioSpec (Old)
- Complex JSON schema with actions, preconditions, effects
- JSONLogic conditions for rule enforcement
- Monte Carlo simulations for difficulty balancing
- Random events with weights
- Loss conditions and negativity budgets
- High complexity, steep learning curve

### Simplified Scenarios (New, Default)
- Rich world background narratives
- Detailed character profiles with personalities and goals
- Dynamic LLM-powered narrative generation
- No rigid rules or preconditions
- No Monte Carlo validation needed
- Much faster generation
- More creative freedom

## Architecture

### Data Models

**WorldBackground**
```python
{
  "description": "3-5 paragraph world description",
  "themes": ["theme1", "theme2"],
  "setting": "Time period and location",
  "key_locations": ["location1", "location2"],
  "factions": ["faction1", "faction2"],
  "tone": "dark/light/balanced"
}
```

**CharacterProfile**
```python
{
  "id": "character_id",
  "name": "Character Name",
  "background": "Detailed 2-3 paragraph background",
  "personality_traits": ["trait1", "trait2"],
  "goals": ["goal1", "goal2"],
  "relationships": {"char_id": "relationship description"},
  "memories": [
    {
      "content": "Memory text",
      "importance": 8,  // 1-10
      "scope": "general/relationship/knowledge",
      "turn": 0
    }
  ]
}
```

**SimplifiedScenario**
```python
{
  "id": "scenario_id",
  "name": "Scenario Name",
  "description": "Original user description",
  "world_background": WorldBackground,
  "characters": [CharacterProfile],
  "initial_state": {},  // Optional game state
  "suggested_actions": ["explore", "talk", "fight"],  // Hints, not rules
  "difficulty_hints": {"difficulty": "balanced"}
}
```

## API Usage

### Generating a Simplified Scenario (Default)

```bash
POST /scenarios/generate
Content-Type: application/json

{
  "description": "A mystery in Victorian London where a detective must solve a murder",
  "num_characters": 3,
  "include_player": true,
  "player_name": "Detective Holmes",
  "difficulty": "balanced"
}
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "The Mystery of Whitechapel",
  "status": "generated",
  "character_count": 3,
  "has_world_background": true
}
```

### Generating a Legacy ScenarioSpec

For backward compatibility, use the `use_legacy=true` query parameter:

```bash
POST /scenarios/generate?use_legacy=true
Content-Type: application/json

{
  "description": "Same description"
}
```

### Creating a Session

Session creation automatically detects the scenario type:

```bash
POST /sessions/
Content-Type: application/json

{
  "scenario_id": "550e8400-e29b-41d4-a716-446655440000",
  "config": {
    "player_name": "Alex"
  }
}
```

### Processing Turns

The same API works for both scenario types:

```bash
POST /sessions/{session_id}/turn
Content-Type: application/json

{
  "action": "Examine the crime scene carefully"
}
```

## How It Works

### Scenario Generation Flow

1. **World Background Generation**
   - LLM generates 3-5 paragraph world description
   - Extracts themes, setting, locations, factions
   - Determines appropriate tone

2. **Character Profile Generation**
   - Creates detailed character backgrounds (200-400 words each)
   - Generates personality traits and goals
   - Establishes initial relationships
   - Creates starter memories

3. **Suggested Actions**
   - Analyzes world themes and tone
   - Generates appropriate action types (not rigid rules)
   - Provides hints to the narrator LLM

4. **Storage**
   - Stores with type marker: `{"type": "simplified", "data": {...}}`
   - Fast compilation (no Monte Carlo)

### Turn Processing Flow

1. **Context Building**
   - Loads world background
   - Gets character profiles and memories
   - Retrieves recent turn history

2. **Narrative Generation**
   - Builds rich context for LLM
   - Includes world setting, characters, memories
   - Generates dynamic narrative (2-4 paragraphs)
   - No rule checking or validation

3. **Memory Updates**
   - Can optionally track character memories
   - Updates emotional states
   - Records relationship changes

## Benefits

### For Users
- **Faster generation**: No Monte Carlo simulation
- **More creative freedom**: No rigid rules to constrain storytelling
- **Easier to understand**: Simple world + characters model
- **Better narratives**: Focus on story quality over mechanics

### For Developers
- **Simpler architecture**: Less complexity to maintain
- **Easier debugging**: Fewer moving parts
- **More flexible**: Easy to extend and customize
- **Better LLM integration**: Leverages LLM strengths

## Migration Guide

### For Existing Scenarios

Legacy ScenarioSpec scenarios continue to work:
- Existing sessions work unchanged
- Old API endpoints remain functional
- Use `use_legacy=true` to generate new legacy scenarios

### Recommended Approach

1. **New projects**: Use simplified scenarios (default)
2. **Existing projects**: Keep using legacy scenarios
3. **Gradual migration**: Create new scenarios as simplified
4. **No forced migration**: Both systems coexist

## Performance Comparison

| Metric | Legacy ScenarioSpec | Simplified Scenario |
|--------|---------------------|---------------------|
| Generation time | 30-60 seconds | 10-20 seconds |
| Compilation time | 15-30 seconds (Monte Carlo) | < 1 second |
| Complexity | High | Low |
| LLM calls | 3-5 | 2-3 |
| Memory usage | Higher | Lower |
| Creative freedom | Limited by rules | Unlimited |

## Best Practices

### Writing Scenario Descriptions

Be descriptive but concise:
```
Good: "A cyberpunk detective story in Neo Tokyo where corporate espionage threatens the city's AI infrastructure"

Less good: "Make a story about a detective"
```

### Character Count

- **1-2 characters**: Simple, focused stories
- **3-5 characters**: Balanced complexity (recommended)
- **6-10 characters**: Complex, ensemble stories

### Difficulty Settings

- **easy**: Lighter tone, fewer complications
- **balanced**: Mixed challenges (default)
- **hard**: Darker tone, more challenging situations

## Troubleshooting

### Scenario generation fails

Check:
- Description is not too vague
- LLM provider is configured correctly
- API key is valid
- Network connectivity

### Session creation fails

Check:
- Scenario exists and is compiled
- Database has space
- No conflicting session IDs

### Narrative quality issues

Try:
- More detailed character backgrounds
- Clearer world description
- Adjust difficulty setting
- Use different LLM model

## Future Enhancements

Planned improvements:
- [ ] Streaming narrative generation
- [ ] Multi-language support
- [ ] Custom character templates
- [ ] World background templates
- [ ] Export/import scenarios
- [ ] Scenario marketplace

## Support

For issues or questions:
- GitHub Issues: https://github.com/AB-Law/QuietStories/issues
- Documentation: https://github.com/AB-Law/QuietStories/blob/main/README.md
