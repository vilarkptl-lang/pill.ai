<script lang="ts">
  import { tick } from "svelte";

  let {
    messages = [],
    thinking = false,
    onSend,
    onClose,
    onDragStart = async () => {},
  }: {
    messages: { role: string; content: string }[];
    thinking: boolean;
    onSend: (text: string) => void;
    onClose: () => void;
    onDragStart?: () => Promise<void>;
  } = $props();

  let input = $state("");
  let listEl: HTMLElement;

  $effect(() => {
    // scroll to bottom whenever messages change
    void messages;
    tick().then(() => {
      if (listEl) listEl.scrollTop = listEl.scrollHeight;
    });
  });

  function submit() {
    const text = input.trim();
    if (!text || thinking) return;
    input = "";
    onSend(text);
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }
</script>

<div class="panel">
  <header onmousedown={() => onDragStart()}>
    <span class="logo">pill.ai</span>
    <button class="close" onclick={onClose} aria-label="Cerrar">✕</button>
  </header>

  <div class="messages" bind:this={listEl}>
    {#if messages.length === 0 && !thinking}
      <p class="empty">¿En qué puedo ayudarte?</p>
    {/if}

    {#each messages as msg}
      <div class="msg {msg.role}">
        {msg.content}
      </div>
    {/each}

    {#if thinking}
      <div class="msg assistant dots">
        <span></span><span></span><span></span>
      </div>
    {/if}
  </div>

  <div class="input-row">
    <textarea
      bind:value={input}
      onkeydown={onKeydown}
      placeholder="Escribe algo…"
      rows="1"
      disabled={thinking}
    ></textarea>
    <button class="send" onclick={submit} disabled={thinking || !input.trim()}>↑</button>
  </div>
</div>

<style>
  .panel {
    width: 340px;
    height: 420px;
    display: flex;
    flex-direction: column;
    background: rgba(10, 10, 16, 0.84);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.65), 0 0 0 0.5px rgba(255,255,255,0.06);
    font-family: "Segoe UI", system-ui, sans-serif;
    color: #f4f4f4;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    cursor: grab;
    flex-shrink: 0;
  }

  header:active { cursor: grabbing; }

  .logo {
    font-size: 13px;
    font-weight: 700;
    color: #0f62fe;
    letter-spacing: 0.4px;
  }

  .close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.35);
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: color 0.15s;
    line-height: 1;
  }
  .close:hover { color: rgba(255, 255, 255, 0.8); }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,0.08) transparent;
  }

  .empty {
    color: rgba(255, 255, 255, 0.28);
    font-size: 13px;
    text-align: center;
    margin: auto;
  }

  .msg {
    max-width: 88%;
    padding: 8px 12px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .msg.user {
    background: #0f62fe;
    color: #fff;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
  }

  .msg.assistant {
    background: rgba(255, 255, 255, 0.07);
    color: #f4f4f4;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
  }

  .msg.dots {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 12px 14px;
  }

  .msg.dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(255,255,255,0.35);
    animation: bounce 1.2s ease-in-out infinite;
  }
  .msg.dots span:nth-child(2) { animation-delay: 0.2s; }
  .msg.dots span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0);   opacity: 0.35; }
    40%           { transform: translateY(-5px); opacity: 1; }
  }

  .input-row {
    display: flex;
    gap: 8px;
    padding: 10px 14px;
    border-top: 1px solid rgba(255,255,255,0.07);
    align-items: flex-end;
    flex-shrink: 0;
  }

  textarea {
    flex: 1;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: #f4f4f4;
    font-family: inherit;
    font-size: 13px;
    padding: 8px 10px;
    resize: none;
    outline: none;
    max-height: 80px;
    overflow-y: auto;
    line-height: 1.45;
  }
  textarea::placeholder { color: rgba(255,255,255,0.22); }
  textarea:focus { border-color: rgba(15,98,254,0.55); }
  textarea:disabled { opacity: 0.45; }

  .send {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #0f62fe;
    border: none;
    color: #fff;
    font-size: 17px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, opacity 0.15s;
    flex-shrink: 0;
    line-height: 1;
  }
  .send:hover:not(:disabled) { background: #0353e9; }
  .send:disabled { opacity: 0.38; cursor: default; }
</style>
