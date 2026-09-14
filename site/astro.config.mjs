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
			// Same double-diamond mark as the IIIF Cloud Services docs, in a teal a couple of steps
			// darker than Digirati's #00d0b8 accent (#0d9488, overlap #115e59). Wordmark set in Public
			// Sans Bold and converted to paths. Two files because the wordmark is black on light and
			// white on dark. The same mark is the favicon and the home page hero.
			logo: {
				light: './src/assets/logo-light.svg',
				dark: './src/assets/logo-dark.svg',
				alt: 'Digital Preservation',
				replacesTitle: true
			},
			// Several pages describe work in flight. The originals carried "as of August 2026"
			// style anchors; this dates every page from its last commit instead.
			lastUpdated: true,
			// Teal accent to go with the logo; see the file for what it recolours.
			customCss: ['./src/styles/custom.css'],
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
