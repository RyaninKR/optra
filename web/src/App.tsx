import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import { ChatView } from "./components/ChatView";
import { LandingView } from "./components/LandingView";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const { messages, conversationId, conversationTitle, isStreaming, error, send, stop, reset } = useChat();
  const { status } = useAuth();

  const hasMessages = messages.length > 0;

  const currentConversation = conversationId
    ? { id: conversationId, title: conversationTitle || "새 대화" }
    : null;

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary">
      <Sidebar
        slackConnected={status.slack.connected}
        notionConnected={status.notion.connected}
        currentConversation={currentConversation}
        onNewChat={reset}
      />

      {hasMessages ? (
        <ChatView
          messages={messages}
          onSend={send}
          isStreaming={isStreaming}
          error={error}
          onStop={stop}
        />
      ) : (
        <LandingView onSend={send} disabled={isStreaming} />
      )}
    </div>
  );
}
