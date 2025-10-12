# QuietStories Frontend

A modern React + TypeScript frontend for the QuietStories Dynamic CYOA Engine.

## Features

### 🎮 Chat Interface
- **Create Sessions**: Start new interactive story sessions by describing your scenario
- **Real-time Interaction**: Chat with the AI narrator and make choices that shape your story
- **Message History**: View complete conversation history with turn tracking
- **Session Management**: Create new sessions or continue existing ones

### 🛡️ Admin Panel
- **Session Overview**: View all active sessions with key metrics
- **Dynamic Memory Viewer**: Inspect character memories (both private and public)
- **State Inspector**: View complete game state in a readable format
- **Real-time Updates**: Refresh data to see the latest information

### 🎨 UI Components
- **Modern Design**: Built with Tailwind CSS for a clean, responsive interface
- **Dark Mode**: Toggle between light and dark themes
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Custom Components**: Reusable UI components (Button, Card, Input, Tabs)

## Getting Started

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start the development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/         # React components
│   │   ├── ui/            # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Tabs.tsx
│   │   ├── AdminPanel.tsx # Admin dashboard
│   │   ├── Chat.tsx       # Chat interface
│   │   ├── Home.tsx       # Landing page
│   │   └── Layout.tsx     # App layout with navigation
│   ├── services/          # API services
│   │   └── api.ts         # FastAPI backend communication
│   ├── lib/               # Utility functions
│   │   └── utils.ts       # Helper utilities
│   ├── App.tsx            # Main app component with routing
│   ├── main.tsx           # App entry point
│   └── index.css          # Global styles
├── public/                # Static assets
└── package.json           # Dependencies and scripts
```

## Usage

### Starting a New Story

1. Navigate to the **Chat** page
2. Enter a scenario description (e.g., "A detective investigating a mysterious disappearance")
3. Click "Create Session"
4. Once the session is created, start typing your actions!

### Using the Admin Panel

1. Navigate to the **Admin** page
2. View all active sessions in the left panel
3. Click on a session to view its details
4. Use the tabs to switch between:
   - **State**: View the complete game state
   - **Memories**: Inspect character memories

### Theme Switching

Click the moon/sun icon in the header to toggle between light and dark modes.

## API Integration

The frontend communicates with the FastAPI backend using the following endpoints:

- `POST /scenarios/generate` - Generate a new scenario
- `POST /scenarios/{id}/compile` - Compile a scenario
- `POST /sessions/` - Create a new session
- `GET /sessions/` - List all sessions
- `GET /sessions/{id}` - Get session details
- `POST /sessions/{id}/turns` - Process a turn

## Technologies

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Navigation
- **Tailwind CSS** - Styling
- **Lucide React** - Icons

## Build for Production

```bash
# Build the app
npm run build

# Preview the production build
npm run preview
```

## Contributing

This frontend is designed to be extensible and modular. To add new features:

1. Create components in `src/components/`
2. Add API methods in `src/services/api.ts`
3. Update routes in `src/App.tsx` if needed

## Notes

- The admin panel dynamically renders any data structure from the backend
- Memory viewing supports both private and public memory types
- The chat interface automatically scrolls to the latest message
- All API calls include proper error handling
