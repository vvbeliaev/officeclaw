import { betterAuth } from 'better-auth/minimal';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';
import { sveltekitCookies } from 'better-auth/svelte-kit';
import { emailOTP } from 'better-auth/plugins';
import { env } from '$env/dynamic/private';
import { getRequestEvent } from '$app/server';
import { db } from '$lib/server/db';

const BOOTSTRAP_ATTEMPTS = 3;
const BOOTSTRAP_BACKOFF_MS = [250, 750, 2000];

async function bootstrapUserWithRetry(userId: string): Promise<void> {
	let lastError: unknown;
	for (let attempt = 0; attempt < BOOTSTRAP_ATTEMPTS; attempt++) {
		try {
			const resp = await fetch(`${env.API_URL}/users/${userId}/bootstrap`, { method: 'POST' });
			// The API is idempotent — both 201 (first bootstrap) and 409
			// (race where another attempt won) mean the user is now bootstrapped.
			if (resp.ok || resp.status === 409) return;
			lastError = new Error(`bootstrap returned ${resp.status}: ${await resp.text()}`);
		} catch (err) {
			lastError = err;
		}
		if (attempt < BOOTSTRAP_ATTEMPTS - 1) {
			await new Promise((resolve) => setTimeout(resolve, BOOTSTRAP_BACKOFF_MS[attempt]));
		}
	}
	// Surface the failure — better-auth will propagate to the sign-up response
	// so the caller knows the account is unusable instead of silently stranding
	// a half-created user.
	throw new Error(`[auth] bootstrap failed for user ${userId}: ${lastError}`);
}

export const auth = betterAuth({
	baseURL: env.ORIGIN!,
	secret: env.BETTER_AUTH_SECRET!,
	database: drizzleAdapter(db, { provider: 'pg' }),
	advanced: {
		database: {
			generateId: () => crypto.randomUUID()
		}
	},

	emailAndPassword: { enabled: true },

	socialProviders: {
		google: {
			clientId: env.GOOGLE_CLIENT_ID!,
			clientSecret: env.GOOGLE_CLIENT_SECRET!
		}
	},

	databaseHooks: {
		user: {
			create: {
				after: async (user) => {
					await bootstrapUserWithRetry(user.id);
				}
			}
		}
	},

	plugins: [
		emailOTP({
			sendVerificationOTP: async ({ email, otp, type }) => {
				// TODO: replace with your email provider (Resend, Nodemailer, etc.)
				// type: 'sign-in' | 'email-verification' | 'forget-password'
				console.log(`[auth] OTP for ${email} (${type}): ${otp}`);
			},
			expiresIn: 300 // 5 minutes
		}),
		sveltekitCookies(getRequestEvent) // must be last
	]
});
