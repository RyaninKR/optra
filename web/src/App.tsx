import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import { ChatView } from "./components/ChatView";
import { LandingView } from "./components/LandingView";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const { messages, isStreaming, error, send, reset } = useChat();
  const { status } = useAuth();

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary">
      <Sidebar
        slackConnected={status.slack.connected}
        notionConnected={status.notion.connected}
        onNewChat={reset}
      />

      {hasMessages ? (
        <ChatView
          messages={messages}
          onSend={send}
          isStreaming={isStreaming}
          error={error}
        />
      ) : (
        <LandingView onSend={send} disabled={isStreaming} />
      )}
    </div>
  );
}
