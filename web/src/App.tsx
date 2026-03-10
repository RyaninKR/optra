import { useCallback, useEffect } from "react";
import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import { useConversations } from "./hooks/useConversations";
import { ChatView } from "./components/ChatView";
import { LandingView } from "./components/LandingView";
import { Sidebar } from "./components/Sidebar";

export default function App() {
  const {
    messages,
    conversationId,
    isStreaming,
    error,
    send,
    stop,
    reset,
    loadConversation,
  } = useChat();
  const { status, connecting, connect, disconnect } = useAuth();
  const { conversations, refresh: refreshConversations, remove: removeConversation } = useConversations();

  // Refresh conversation list when streaming ends (new conversation or title update)
  useEffect(() => {
    if (!isStreaming && conversationId) {
      refreshConversations();
    }
  }, [isStreaming, conversationId, refreshConversations]);

  // Initial fetch
  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      if (id === conversationId) return;
      loadConversation(id);
    },
    [conversationId, loadConversation],
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      await removeConversation(id);
      if (id === conversationId) {
        reset();
      }
    },
    [conversationId, removeConversation, reset],
  );

  const handleNewChat = useCallback(() => {
    reset();
  }, [reset]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary">
      <Sidebar
        slackStatus={status.slack}
        notionStatus={status.notion}
        connecting={connecting}
        conversations={conversations}
        activeConversationId={conversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
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
