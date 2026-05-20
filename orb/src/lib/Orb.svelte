<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import ChatPanel from "./ChatPanel.svelte";
  import PlayStopButton from "./PlayStopButton.svelte";

  const ORB_W = 60, ORB_H = 60;
  const PANEL_W = 340, PANEL_H = 420;

  let expanded = $state(false);
  let thinking = $state(false);
  let messages = $state<{ role: string; content: string }[]>([]);

  // click vs drag detection
  let dragTimer: ReturnType<typeof setTimeout> | null = null;
  let didDrag = false;

  function onMouseDown() {
    didDrag = false;
    dragTimer = setTimeout(async () => {
      didDrag = true;
      await invoke("start_drag").catch(() => {});
    }, 180);
  }

  function onMouseUp() {
    if (dragTimer) { clearTimeout(dragTimer); dragTimer = null; }
  }

  function onClick() {
    if (!didDrag) toggle();
  }

  async function toggle() {
    expanded = !expanded;
    await invoke("resize_window", {
      width:  expanded ? PANEL_W : ORB_W,
      height: expanded ? PANEL_H : ORB_H,
    }).catch(() => {});
  }

  async function sendMessage(text: string) {
    if (thinking) return;
    messages = [...messages, { role: "user", content: text }];
    thinking = true;
    try {
      const result = await invoke<string>("chat", { message: text });
      messages = [...messages, { role: "assistant", content: result }];
    } catch (e) {
      messages = [...messages, { role: "assistant", content: `Error: ${e}` }];
    } finally {
      thinking = false;
    }
  }

  async function handleDrag() {
    await invoke("start_drag").catch(() => {});
  }
</script>

<div class="root" class:expanded>
  {#if !expanded}
    <button
      class="orb"
      onmousedown={onMouseDown}
      onmouseup={onMouseUp}
      onclick={onClick}
      aria-label="Abrir pill.ai"
    >
      <PlayStopButton {thinking} />
    </button>
  {:else}
    <ChatPanel
      {messages}
      {thinking}
      onSend={sendMessage}
      onClose={toggle}
      onDragStart={handleDrag}
    />
  {/if}
</div>

<style>
  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) { background: transparent !important; overflow: hidden; }

  .root {
    width: 60px;
    height: 60px;
  }

  .orb {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: rgba(15, 98, 254, 0.18);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.22);
    box-shadow:
      0 8px 32px rgba(15, 98, 254, 0.38),
      inset 0 1px 0 rgba(255, 255, 255, 0.18);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s, box-shadow 0.2s, transform 0.14s;
    outline: none;
    padding: 0;
    animation: pulse 3s ease-in-out infinite;
  }

  .orb:hover {
    background: rgba(15, 98, 254, 0.30);
    box-shadow:
      0 12px 40px rgba(15, 98, 254, 0.52),
      inset 0 1px 0 rgba(255, 255, 255, 0.28);
    transform: scale(1.07);
    animation: none;
  }

  .orb:active { transform: scale(0.94); }

  @keyframes pulse {
    0%, 100% { box-shadow: 0 8px 32px rgba(15,98,254,0.38), inset 0 1px 0 rgba(255,255,255,0.18); }
    50%       { box-shadow: 0 8px 40px rgba(15,98,254,0.60), inset 0 1px 0 rgba(255,255,255,0.22); }
  }
</style>
