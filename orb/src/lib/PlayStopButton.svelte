<script lang="ts">
  let { thinking = false }: { thinking: boolean } = $props();
</script>

<div class="btn" class:thinking>
  {#if thinking}
    <svg class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
  {:else}
    <svg viewBox="0 0 24 24" fill="currentColor">
      <polygon points="6,3 20,12 6,21"/>
    </svg>
  {/if}
</div>

<style>
  .btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.92);
    pointer-events: none;
  }

  svg {
    width: 20px;
    height: 20px;
  }

  .thinking svg {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
</style>
