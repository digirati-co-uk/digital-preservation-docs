// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://digirati-co-uk.github.io',
	base: '/digital-preservation-docs',
	integrations: [
		starlight({
			title: 'Digital Preservation',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/digirati-co-uk/digital-preservation' }],
			sidebar: [
				{
					label: 'Introduction',
					autogenerate: { directory: 'introduction' }
				},
				{
					label: 'Preservation API',
					collapsed: false,
					autogenerate: { directory: 'preservation-api' }
				},
				{
					label: 'Workflows',
					collapsed: true,
					autogenerate: { directory: 'workflows' }
				},
				{
					label: 'METS',
					collapsed: true,
					autogenerate: { directory: 'mets' }
				},
				{
					label: 'Preservation UI',
					collapsed: true,
					autogenerate: { directory: 'ui' }
				},
				{
					label: 'Storage API',
					collapsed: true,
					autogenerate: { directory: 'storage-api' }
				},
				{
					label: 'Internals',
					collapsed: true,
					autogenerate: { directory: 'internals' }
				},
			],
		}),
	],
});
