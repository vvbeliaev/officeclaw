import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { userEnvs } from '$lib/server/db/app.schema';
import { eq, desc } from 'drizzle-orm';
import type { PageServerLoad } from './$types';

const SECTIONS = {
	skills: {
		title: 'Skills',
		tagline: 'reusable capabilities you teach once and wire into any agent.'
	},
	environments: {
		title: 'Environments',
		tagline: 'secrets and configuration — encrypted at rest, scoped per agent.'
	},
	channels: {
		title: 'Channels',
		tagline: 'where your agents listen and reply — Telegram, Discord, email.'
	},
	knowledge: {
		title: 'Knowledge',
		tagline: 'documents, notes, and sources your fleet can draw from.'
	}
} as const;

type SectionKey = keyof typeof SECTIONS;

export const load: PageServerLoad = async ({ params, locals }) => {
	if (!(params.section in SECTIONS)) error(404, 'Unknown workspace section');
	const key = params.section as SectionKey;
	const section = SECTIONS[key];

	if (key !== 'environments') return { section, key, envs: null };

	const userId = locals.user!.id;
	const envs = await db
		.select({
			id: userEnvs.id,
			name: userEnvs.name,
			createdAt: userEnvs.createdAt
		})
		.from(userEnvs)
		.where(eq(userEnvs.userId, userId))
		.orderBy(desc(userEnvs.createdAt));

	return { section, key, envs };
};
