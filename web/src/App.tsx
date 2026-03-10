import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import { ChatView } from "./components/ChatView";
import { LandingView } from "./components/LandingView";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const { messages, conversationId, conversationTitle, isStreaming, error, send, stop, reset } = useChat();
  const { status, connecting, connect, disconnect } = useAuth();

  const hasMessages = messages.length > 0;

  const currentConversation = conversationId
    ? { id: conversationId, title: conversationTitle || "새 대화" }
    : null;

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary">
      <Sidebar
        slackStatus={status.slack}
        notionStatus={status.notion}
        connecting={connecting}
        currentConversation={currentConversation}
        onNewChat={reset}
        onConnect={connect}
        onDisconnect={disconnect}
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
        <LandingView
          onSend={send}
          disabled={isStreaming}
          slackConnected={status.slack.connected}
          notionConnected={status.notion.connected}
          connecting={connecting}
          onConnect={connect}
        />
      )}
    </div>
  );
}
