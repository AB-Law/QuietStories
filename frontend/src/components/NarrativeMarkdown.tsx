import ReactMarkdown from 'react-markdown';

interface NarrativeMarkdownProps {
  children: string;
  className?: string;
}



// Custom renderer for blockquotes (often used for dialogue)
const BlockquoteComponent = ({ children, ...props }: any) => (
  <blockquote {...props} className="dialogue my-2 pl-4 border-l-2 border-primary italic text-foreground/90 bg-muted/20 rounded-r-md py-2 pr-3">
    {children}
  </blockquote>
);

// Custom renderer for paragraphs with enhanced formatting
const ParagraphComponent = ({ children, ...props }: any) => {
  // Convert children to string to check for dialogue patterns
  const text = typeof children === 'string' ? children : String(children);

  // Check if this paragraph contains dialogue (starts with quote or character name followed by colon)
  const isDialogue = /^["']/.test(text) || /^[A-Z][a-zA-Z\s]+:/.test(text);

  if (isDialogue) {
    return (
      <div className="dialogue my-2 pl-4 border-l-2 border-primary bg-muted/10 rounded-r-md py-2 pr-3">
        <p {...props} className="prose-p italic text-foreground/90 mb-0">
          {children}
        </p>
      </div>
    );
  }

  return (
    <p {...props} className="prose-p text-foreground leading-relaxed my-3">
      {children}
    </p>
  );
};



export function NarrativeMarkdown({ children, className = '' }: NarrativeMarkdownProps) {
  return (
    <div className={`narrative-content prose prose-sm sm:prose lg:prose-lg max-w-none dark:prose-invert ${className}`}>
      <ReactMarkdown
        components={{
          // Override default components with our custom ones
          blockquote: BlockquoteComponent,
          p: ParagraphComponent,
          // Strong and emphasis with better styling
          strong: ({ children, ...props }: any) => (
            <strong {...props} className="font-semibold text-foreground">
              {children}
            </strong>
          ),
          em: ({ children, ...props }: any) => (
            <em {...props} className="italic text-foreground/90">
              {children}
            </em>
          ),
          // Headers with proper styling
          h1: ({ children, ...props }: any) => (
            <h1 {...props} className="text-xl font-bold text-foreground mb-2 mt-4 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children, ...props }: any) => (
            <h2 {...props} className="text-lg font-semibold text-foreground mb-2 mt-3">
              {children}
            </h2>
          ),
          h3: ({ children, ...props }: any) => (
            <h3 {...props} className="text-base font-semibold text-foreground mb-1 mt-2">
              {children}
            </h3>
          ),
          // Lists with proper spacing
          ul: ({ children, ...props }: any) => (
            <ul {...props} className="list-disc list-inside space-y-1 my-2 text-foreground">
              {children}
            </ul>
          ),
          ol: ({ children, ...props }: any) => (
            <ol {...props} className="list-decimal list-inside space-y-1 my-2 text-foreground">
              {children}
            </ol>
          ),
          li: ({ children, ...props }: any) => (
            <li {...props} className="text-foreground leading-relaxed">
              {children}
            </li>
          ),
          // Code blocks
          code: ({ children, className, ...props }: any) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code {...props} className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">
                  {children}
                </code>
              );
            }
            return (
              <code {...props} className="block bg-muted p-3 rounded text-sm font-mono text-foreground overflow-x-auto">
                {children}
              </code>
            );
          },
          // Horizontal rules
          hr: () => (
            <hr className="my-4 border-border" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
