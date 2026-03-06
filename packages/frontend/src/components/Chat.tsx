import { useRef, useState, useEffect, type FormEvent } from "react";
import { useAppStore } from "../stores/appStore";

export function Chat() {
  const messages = useAppStore((s) => s.messages);
  const isSending = useAppStore((s) => s.isSending);
  const sendMessage = useAppStore((s) => s.sendMessage);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isSending) return;
    setInput("");
    sendMessage(text);
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-msg chat-msg--${msg.role}`}>
            <span className="chat-msg__role">
              {msg.role === "user" ? "You" : "AI"}
            </span>
            <p className="chat-msg__text">{msg.content}</p>
          </div>
        ))}
        {isSending && (
          <div className="chat-msg chat-msg--assistant">
            <span className="chat-msg__role">AI</span>
            <p className="chat-msg__text chat-msg__text--typing">Thinking…</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your building…"
          disabled={isSending}
        />
        <button type="submit" disabled={isSending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
