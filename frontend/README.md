# Context Engineering Sandbox - Frontend

React + TypeScript frontend for the Context Engineering Sandbox project, featuring AG-UI protocol integration and real-time agent interaction.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling framework
- **Shadcn/UI** - Beautiful UI components
- **CopilotKit (AG-UI)** - Agent-User Interaction Protocol
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **React Router** - Navigation

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5173

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── ui/         # Shadcn/UI components
│   │   ├── chat/       # AG-UI chat components
│   │   ├── metrics/    # Metrics display
│   │   ├── layout/     # Layout components
│   │   └── common/     # Shared components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── services/       # API services
│   ├── types/          # TypeScript types
│   ├── lib/            # Utilities
│   └── styles/         # Global styles
├── public/             # Static assets
└── index.html          # Entry HTML
```

## Features

### 1. Interactive Chat Interface

- Real-time communication with ADK agent
- WebSocket streaming support
- Thinking process visualization
- Tool call display
- AG-UI protocol integration

### 2. Metrics Dashboard

- Real-time performance metrics
- Phase comparison charts
- Improvement tracking
- Visual analytics with Recharts

### 3. Responsive Design

- Mobile-first approach
- Dark mode support (via Shadcn/UI)
- Accessible components
- Modern UI/UX

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Environment Variables

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENV=development
```

## AG-UI Integration

This frontend uses the [AG-UI protocol](https://github.com/ag-ui-protocol/ag-ui) via CopilotKit to provide seamless agent-user interaction:

- **Real-time context sharing** between UI and agent
- **Action handlers** for agent tools
- **Streaming responses** during agent execution
- **Readable state** for agent awareness

## Contributing

See the main project README for contribution guidelines.

## License

MIT

