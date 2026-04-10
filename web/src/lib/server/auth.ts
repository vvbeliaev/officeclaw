import { betterAuth } from 'better-auth/minimal';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';
import { sveltekitCookies } from 'better-auth/svelte-kit';
import { emailOTP } from 'better-auth/plugins';
import { env } from '$env/dynamic/private';
import { getRequestEvent } from '$app/server';
import { db } from '$lib/server/db';

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
					// Bootstrap Admin agent for every new user
					await fetch(`${env.API_URL}/users/${user.id}/bootstrap`, {
						method: 'POST'
					}).catch((err) => {
						console.error('[auth] bootstrap failed for user', user.id, err);
					});
				}
			}
		}
	},

	user: {
		additionalFields: {
			officeclawToken: {
				type: 'string',
				required: false,
				input: false
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
