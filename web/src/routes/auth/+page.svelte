<script lang="ts">
	import { goto } from '$app/navigation';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Separator } from '$lib/components/ui/separator';
	import { Icon } from '$lib/icons';

	let mode = $state<'signin' | 'signup'>('signin');
	let email = $state('');
	let password = $state('');
	let name = $state('');
	let loading = $state(false);
	let error = $state('');

	async function submit() {
		loading = true;
		error = '';
		try {
			if (mode === 'signin') {
				const { error: err } = await authClient.signIn.email({
					email,
					password,
					callbackURL: '/'
				});
				if (err) error = err.message ?? 'Sign in failed';
				else await goto('/');
			} else {
				const { error: err } = await authClient.signUp.email({
					email,
					password,
					name,
					callbackURL: '/'
				});
				if (err) error = err.message ?? 'Sign up failed';
				else await goto('/');
			}
		} catch {
			error = 'Something went wrong';
		} finally {
			loading = false;
		}
	}

	async function signInWithGoogle() {
		await authClient.signIn.social({ provider: 'google', callbackURL: '/' });
	}
</script>

<div class="min-h-screen flex flex-col items-center justify-center px-4">
	<!-- Logo -->
	<a href="/" class="flex items-center gap-3 mb-10 no-underline">
		<div
			class="w-9 h-9 bg-primary flex items-center justify-center shrink-0"
			style="clip-path: polygon(0 0, 100% 0, 100% 75%, 75% 100%, 0 100%)"
		>
			<Icon icon="oc:claw" width={18} height={18} class="text-primary-foreground" />
		</div>
		<span class="text-lg font-medium text-foreground tracking-tight">
			Office<span class="font-bold">Claw</span>
		</span>
	</a>

	<!-- Card -->
	<div class="w-full max-w-sm bg-card border border-border rounded-lg p-7">
		<!-- Mode toggle -->
		<div class="flex gap-1 mb-6 p-1 bg-muted rounded">
			<button
				class="flex-1 py-1.5 text-sm rounded transition-colors {mode === 'signin'
					? 'bg-background text-foreground shadow-sm'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => {
					mode = 'signin';
					error = '';
				}}
			>
				Sign in
			</button>
			<button
				class="flex-1 py-1.5 text-sm rounded transition-colors {mode === 'signup'
					? 'bg-background text-foreground shadow-sm'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => {
					mode = 'signup';
					error = '';
				}}
			>
				Sign up
			</button>
		</div>

		<form
			onsubmit={(e) => {
				e.preventDefault();
				submit();
			}}
			class="space-y-4"
		>
			{#if mode === 'signup'}
				<div class="space-y-1.5">
					<Label for="name">Name</Label>
					<Input id="name" type="text" placeholder="Your name" bind:value={name} required />
				</div>
			{/if}

			<div class="space-y-1.5">
				<Label for="email">Email</Label>
				<Input
					id="email"
					type="email"
					placeholder="you@example.com"
					bind:value={email}
					required
				/>
			</div>

			<div class="space-y-1.5">
				<Label for="password">Password</Label>
				<Input
					id="password"
					type="password"
					placeholder="••••••••"
					bind:value={password}
					required
				/>
			</div>

			{#if error}
				<p class="text-sm text-destructive">{error}</p>
			{/if}

			<Button type="submit" class="w-full" disabled={loading}>
				{#if loading}
					<Icon icon="tabler:loader-2" width={14} height={14} class="animate-spin mr-1.5" />
				{/if}
				{mode === 'signin' ? 'Sign in' : 'Create account'}
			</Button>
		</form>

		<div class="flex items-center gap-3 my-5">
			<Separator class="flex-1" />
			<span class="text-xs text-muted-foreground">or</span>
			<Separator class="flex-1" />
		</div>

		<Button variant="outline" class="w-full gap-2" onclick={signInWithGoogle}>
			<Icon icon="tabler:brand-google" width={15} height={15} />
			Continue with Google
		</Button>
	</div>

	<p class="text-xs text-muted-foreground mt-6">Open-source AI agent fleet manager</p>
</div>
