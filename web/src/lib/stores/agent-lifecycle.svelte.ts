import { invalidateAll } from '$app/navigation';
import { SvelteMap } from 'svelte/reactivity';

export type LifecyclePhase = 'starting' | 'stopping' | 'error';

export type LifecycleEntry = {
	phase: LifecyclePhase;
	error?: string;
};

class AgentLifecycleStore {
	private states = new SvelteMap<string, LifecycleEntry>();

	get(agentId: string): LifecycleEntry | null {
		return this.states.get(agentId) ?? null;
	}

	clear(agentId: string) {
		this.states.delete(agentId);
	}

	dismissError(agentId: string) {
		const entry = this.states.get(agentId);
		if (entry?.phase === 'error') this.states.delete(agentId);
	}

	async start(agentId: string) {
		this.states.set(agentId, { phase: 'starting' });
		try {
			const res = await fetch(`/api/agents/${agentId}/start`, { method: 'POST' });
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			await invalidateAll();
			this.states.delete(agentId);
		} catch (err) {
			this.states.set(agentId, {
				phase: 'error',
				error: err instanceof Error ? err.message : 'Failed to start sandbox'
			});
		}
	}

	async stop(agentId: string) {
		this.states.set(agentId, { phase: 'stopping' });
		try {
			const res = await fetch(`/api/agents/${agentId}/stop`, { method: 'POST' });
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `HTTP ${res.status}`);
			}
			await invalidateAll();
			this.states.delete(agentId);
		} catch (err) {
			this.states.set(agentId, {
				phase: 'error',
				error: err instanceof Error ? err.message : 'Failed to stop sandbox'
			});
		}
	}
}

export const agentLifecycle = new AgentLifecycleStore();
