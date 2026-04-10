import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

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

export const load: PageLoad = ({ params }) => {
	if (!(params.section in SECTIONS)) error(404, 'Unknown workspace section');
	const key = params.section as SectionKey;
	return { section: SECTIONS[key], key };
};
