import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userMcp } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const GET: RequestHandler = async ({ locals }) => {
	const userId = locals.user!.id;
	const mcps = await db
		.select({
			id: userMcp.id,
			name: userMcp.name,
			type: userMcp.type,
			createdAt: userMcp.createdAt
		})
		.from(userMcp)
		.where(eq(userMcp.userId, userId))
		.orderBy(desc(userMcp.createdAt));
	return json(mcps);
};

export const POST: RequestHandler = async ({ request, locals }) => {
	const userId = locals.user!.id;
	const body = await request.json();

	const res = await fetch(`${API_URL}/user-mcp`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ user_id: userId, ...body })
	});

	if (!res.ok) {
		const text = await res.text();
		throw error(res.status, text);
	}

	return json(await res.json(), { status: 201 });
};
