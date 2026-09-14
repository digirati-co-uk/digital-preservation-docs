// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import mermaid from 'astro-mermaid';

// https://astro.build/config
export default defineConfig({
	site: 'https://digirati-co-uk.github.io',
	base: '/digital-preservation-docs',
	integrations: [
		// Renders ```mermaid fences in the browser, following Starlight's light/dark theme.
		// Must come before starlight, or its code highlighter claims the fence first.
		mermaid({ autoTheme: true, logging: false }),
		starlight({
			title: 'Digital Preservation',
			// Several pages describe work in flight. The originals carried "as of August 2026"
			// style anchors; this dates every page from its last commit instead.
			lastUpdated: true,
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
			],
		}),
	],
});
