import { error, json } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userEnvs } from '$lib/server/db/app.schema';
import { and, eq } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const GET: RequestHandler = async ({ params, locals }) => {
	if (!locals.session) error(401, 'Unauthorized');

	// Ownership check before returning decrypted secrets
	const [owned] = await db
		.select({ id: userEnvs.id })
		.from(userEnvs)
		.where(and(eq(userEnvs.id, params.id), eq(userEnvs.userId, locals.user!.id)))
		.limit(1);
	if (!owned) error(404, 'Env not found');

	const upstream = await fetch(`${API_URL}/envs/${params.id}/values`);

	if (!upstream.ok) {
		const text = await upstream.text();
		error(upstream.status, text || 'Failed to fetch env values');
	}

	return json(await upstream.json());
};
