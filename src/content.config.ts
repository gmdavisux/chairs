import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const imageOriginEnum = z.enum([
	'public_domain',
	'licensed',
	'ai_generated',
	'placeholder',
]);

const imageLicenseEnum = z.enum([
	'public_domain',
	'cc0',
	'cc_by',
	'cc_by_sa',
	'licensed',
	'rights_reserved',
	'ai_generated',
	'unknown',
]);

const imageAltStatusEnum = z.enum(['proposed', 'actual']);

const imageRecordSchema = z.object({
	id: z.string(),
	src: z.string(),
	alt: z.string(),
	altStatus: imageAltStatusEnum.default('proposed'),
	caption: z.string().optional(),
	source: z.string().optional(),
	license: imageLicenseEnum.optional(),
	origin: imageOriginEnum.optional(),
});

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.string().optional(),
			heroImageAlt: z.string().optional(),
			heroImageAltStatus: imageAltStatusEnum.optional(),
			heroImageCaption: z.string().optional(),
			heroImageSource: z.string().optional(),
			heroImageLicense: imageLicenseEnum.optional(),
			heroImageOrigin: imageOriginEnum.optional(),
			images: z.array(imageRecordSchema).optional(),
			designer: z.string().optional(),
			designerBio: z.string().optional(),
			designerYears: z.string().optional(),
			designerImage: z.string().optional(),
			era: z.string().optional(),
			category: z.string().optional(),
		}),
});

export const collections = { blog };
