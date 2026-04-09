<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { authClient } from '$lib/auth-client';
	import { Icon } from '$lib/icons';

	let { data, children } = $props();

	const navItems = [
		{ href: '/', label: 'Fleet', icon: 'oc:fleet' },
		{ href: '/tools', label: 'Tools', icon: 'oc:tool' },
		{ href: '/memory', label: 'Memory', icon: 'oc:memory' },
		{ href: '/logs', label: 'Logs', icon: 'oc:log' },
		{ href: '/settings', label: 'Settings', icon: 'oc:configure' }
	] as const;

	function isActive(href: string) {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}

	async function signOut() {
		await authClient.signOut();
		goto('/auth');
	}

	const initials = $derived(
		data.user?.name
			?.split(' ')
			.map((n: string) => n[0])
			.join('')
			.slice(0, 2)
			.toUpperCase() ?? '?'
	);
</script>

<div class="flex min-h-screen">
	<!-- Sidebar -->
	<aside
		class="w-56 shrink-0 flex flex-col border-r"
		style="background: var(--sidebar); border-color: var(--sidebar-border);"
	>
		<!-- Logo -->
		<div
			class="h-14 flex items-center gap-2.5 px-4 border-b shrink-0"
			style="border-color: var(--sidebar-border);"
		>
			<div
				class="w-7 h-7 bg-primary flex items-center justify-center shrink-0"
				style="clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%)"
			>
				<Icon icon="oc:claw" width={13} height={13} class="text-primary-foreground" />
			</div>
			<span
				class="text-sm font-medium tracking-tight"
				style="color: var(--sidebar-foreground)"
			>
				Office<span class="font-bold">Claw</span>
			</span>
		</div>

		<!-- Nav -->
		<nav class="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
			{#each navItems as item}
				<a
					href={item.href}
					class="flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors"
					style={isActive(item.href)
						? 'background: var(--sidebar-accent); color: var(--sidebar-foreground); font-weight: 500;'
						: 'color: color-mix(in oklch, var(--sidebar-foreground) 55%, transparent);'}
					onmouseenter={(e) => {
						if (!isActive(item.href))
							(e.currentTarget as HTMLElement).style.color = 'var(--sidebar-foreground)';
					}}
					onmouseleave={(e) => {
						if (!isActive(item.href))
							(e.currentTarget as HTMLElement).style.color =
								'color-mix(in oklch, var(--sidebar-foreground) 55%, transparent)';
					}}
				>
					<Icon icon={item.icon} width={16} height={16} />
					{item.label}
				</a>
			{/each}
		</nav>

		<!-- User section -->
		<div class="border-t p-3 shrink-0" style="border-color: var(--sidebar-border);">
			<div class="flex items-center gap-2.5 px-2 py-1.5 mb-1">
				<div
					class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
					style="background: color-mix(in oklch, var(--primary) 20%, transparent); color: var(--primary);"
				>
					{initials}
				</div>
				<div class="flex-1 min-w-0">
					<p
						class="text-xs font-medium truncate leading-tight"
						style="color: var(--sidebar-foreground);"
					>
						{data.user?.name ?? 'User'}
					</p>
					<p
						class="text-xs truncate leading-tight"
						style="color: color-mix(in oklch, var(--sidebar-foreground) 45%, transparent);"
					>
						{data.user?.email ?? ''}
					</p>
				</div>
			</div>
			<button
				onclick={signOut}
				class="w-full flex items-center gap-2 px-3 py-1.5 text-xs rounded transition-colors"
				style="color: color-mix(in oklch, var(--sidebar-foreground) 45%, transparent);"
				onmouseenter={(e) => {
					(e.currentTarget as HTMLElement).style.color = 'var(--sidebar-foreground)';
					(e.currentTarget as HTMLElement).style.background = 'var(--sidebar-accent)';
				}}
				onmouseleave={(e) => {
					(e.currentTarget as HTMLElement).style.color =
						'color-mix(in oklch, var(--sidebar-foreground) 45%, transparent)';
					(e.currentTarget as HTMLElement).style.background = 'transparent';
				}}
			>
				<Icon icon="tabler:logout" width={14} height={14} />
				Sign out
			</button>
		</div>
	</aside>

	<!-- Main -->
	<main class="flex-1 flex flex-col min-w-0 overflow-hidden">
		{@render children()}
	</main>
</div>
