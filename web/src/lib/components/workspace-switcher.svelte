<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { Icon } from '$lib/icons';

  interface Workspace {
    id: string;
    name: string;
  }

  let { workspaces, activeWorkspaceId }: { workspaces: Workspace[]; activeWorkspaceId: string } =
    $props();

  let open = $state(false);
  let creating = $state(false);
  let newName = $state('');
  let loading = $state(false);
  let nameInput: HTMLInputElement | null = $state(null);
  let root: HTMLDivElement | null = $state(null);

  const active = $derived(workspaces.find((w) => w.id === activeWorkspaceId));

  function toggle() {
    open = !open;
    if (!open) creating = false;
  }

  function onClickOutside(e: MouseEvent) {
    if (open && root && !root.contains(e.target as Node)) {
      open = false;
      creating = false;
    }
  }

  $effect(() => {
    if (open) {
      document.addEventListener('mousedown', onClickOutside);
      return () => document.removeEventListener('mousedown', onClickOutside);
    }
  });

  function startCreate() {
    creating = true;
    newName = '';
    setTimeout(() => nameInput?.focus(), 0);
  }

  async function createWorkspace() {
    const name = newName.trim();
    if (!name || loading) return;
    loading = true;
    try {
      const res = await fetch('/api/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (!res.ok) return;
      const ws = await res.json();
      open = false;
      creating = false;
      await invalidateAll();
      goto(`/w/${ws.id}`);
    } finally {
      loading = false;
    }
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter') createWorkspace();
    if (e.key === 'Escape') { creating = false; open = false; }
  }
</script>

<div class="switcher" bind:this={root}>
  <button class="trigger font-mono" onclick={toggle} type="button">
    <span class="ws-initial">{active?.name?.[0]?.toUpperCase() ?? '?'}</span>
    <span class="ws-name">{active?.name ?? 'workspace'}</span>
    <Icon icon="tabler:chevron-up-down" width={12} height={12} class="chevron" />
  </button>

  {#if open}
    <div class="popover">
      <ul class="ws-list">
        {#each workspaces as ws (ws.id)}
          <li>
            <button
              class="ws-item font-mono"
              class:active={ws.id === activeWorkspaceId}
              onclick={() => { goto(`/w/${ws.id}`); open = false; }}
              type="button"
            >
              <span class="ws-initial sm">{ws.name[0]?.toUpperCase()}</span>
              {ws.name}
              {#if ws.id === activeWorkspaceId}
                <Icon icon="tabler:check" width={11} height={11} class="check" />
              {/if}
            </button>
          </li>
        {/each}
      </ul>

      <div class="divider"></div>

      {#if creating}
        <div class="create-form">
          <input
            bind:this={nameInput}
            bind:value={newName}
            onkeydown={onKey}
            placeholder="workspace name…"
            class="create-input font-mono"
            maxlength={64}
            disabled={loading}
          />
          <button class="create-confirm font-mono" onclick={createWorkspace} disabled={!newName.trim() || loading} type="button">
            {loading ? 'creating…' : 'create ↵'}
          </button>
        </div>
      {:else}
        <button class="new-btn font-mono" onclick={startCreate} type="button">
          <Icon icon="tabler:plus" width={11} height={11} />
          new workspace
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .switcher {
    position: relative;
  }

  .trigger {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.55rem 0.75rem;
    font-size: 0.72rem;
    color: var(--sidebar-foreground);
    border-top: 1px solid var(--sidebar-border);
    transition: background 150ms ease;
  }

  .trigger:hover {
    background: var(--sidebar-accent);
  }

  .ws-initial {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.62rem;
    font-weight: 700;
    background: color-mix(in oklch, var(--primary) 18%, transparent);
    color: var(--primary);
    flex-shrink: 0;
  }

  .ws-initial.sm {
    width: 16px;
    height: 16px;
    font-size: 0.55rem;
    border-radius: 3px;
  }

  .ws-name {
    flex: 1;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  :global(.chevron) {
    color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
    flex-shrink: 0;
  }

  .popover {
    position: absolute;
    bottom: calc(100% + 4px);
    left: 0.5rem;
    right: 0.5rem;
    background: var(--sidebar);
    border: 1px solid var(--sidebar-border);
    border-radius: 0.4rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    overflow: hidden;
    z-index: 50;
  }

  .ws-list {
    list-style: none;
    padding: 0.3rem;
  }

  .ws-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    padding: 0.35rem 0.5rem;
    font-size: 0.72rem;
    border-radius: 0.25rem;
    color: var(--sidebar-foreground);
    transition: background 120ms ease;
  }

  .ws-item:hover {
    background: var(--sidebar-accent);
  }

  .ws-item.active {
    color: var(--primary);
  }

  :global(.check) {
    margin-left: auto;
    color: var(--primary);
  }

  .divider {
    height: 1px;
    background: var(--sidebar-border);
    margin: 0 0.3rem;
  }

  .new-btn {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    width: 100%;
    padding: 0.45rem 0.8rem;
    font-size: 0.68rem;
    color: color-mix(in oklch, var(--sidebar-foreground) 55%, transparent);
    transition: color 120ms ease, background 120ms ease;
  }

  .new-btn:hover {
    color: var(--sidebar-foreground);
    background: var(--sidebar-accent);
  }

  .create-form {
    padding: 0.5rem 0.6rem;
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }

  .create-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    font-size: 0.72rem;
    color: var(--sidebar-foreground);
  }

  .create-input::placeholder {
    color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
  }

  .create-confirm {
    font-size: 0.62rem;
    color: var(--primary);
    white-space: nowrap;
  }

  .create-confirm:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
</style>
