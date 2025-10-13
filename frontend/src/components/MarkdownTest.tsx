import { NarrativeMarkdown } from './NarrativeMarkdown';

export function MarkdownTest() {
  const testMarkdown = `# Enhanced Narrative Formatting Test

## Story Elements

Here's a sample story with **various formatting** elements to showcase our enhanced markdown rendering.

### Dialogue Example

> "I can't believe we're finally here," Sarah whispered, her eyes wide with wonder as she gazed at the ancient castle before them.

The dialogue above should have special formatting with quote marks and styling.

### Character Actions

*The wind howled through the trees as John carefully approached the mysterious door.*

Actions in italics should be styled differently to indicate narrative descriptions.

### Mixed Content

**Bold text** for emphasis and *italic text* for actions work together beautifully. Here's another dialogue example:

> "What do you think is behind that door?" Tom asked nervously.
>
> "Only one way to find out," replied Sarah with determination.

### Lists and Structure

Things our heroes need:
- Ancient key found in the garden
- Courage to face the unknown
- Trust in each other
- A backup plan

Steps they should follow:
1. Check the door carefully
2. Insert the key slowly
3. Be ready for anything
4. Stay close together

### Code and Technical Elements

Sometimes stories include technical elements like \`magical incantations\` or longer spells:

\`\`\`
Ancient words of power:
Aperio secretum
Revela veritatem
\`\`\`

---

This horizontal rule separates different sections of the story.

> The door creaked open, revealing a passage that seemed to glow with an inner light...

**The adventure continues...**`;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Markdown Rendering Test</h1>
        <p className="text-muted-foreground">
          Testing the enhanced narrative markdown formatting with dialogue, actions, and typography.
        </p>
      </div>

      <div className="border rounded-lg p-6 bg-card">
        <NarrativeMarkdown className="test-narrative">
          {testMarkdown}
        </NarrativeMarkdown>
      </div>
    </div>
  );
}
