import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export const DELETE: RequestHandler = async ({ params }) => {
	const res = await fetch(`${API_URL}/user-mcp/${params.id}`, { method: 'DELETE' });
	if (!res.ok && res.status !== 204) {
		const text = await res.text();
		throw error(res.status, text);
	}
	return new Response(null, { status: 204 });
};
