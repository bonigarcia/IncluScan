Review the language used in the following content to promote inclusive and non-sexist language. Return the response exclusively as valid JSON that can be parsed automatically. The response must be an array of objects. Each object must contain exactly these fields:
- "original": the exact fragment from the original text that should be changed.
- "modified": the adapted version using inclusive and non-sexist language.
- "justification": a brief explanation of why the change was made, in the same language as the original text.

Rules:
- Preserve the original meaning.
- Do not modify proper names, brands, direct quotes, or technical terms unless strictly necessary.
- Avoid artificial or unnatural expressions.
- Prioritize clear, natural, and easy-to-understand alternatives.
- If the adapted text would be effectively the same as the original after normalizing case, spaces, and punctuation, do not report it.
- Do not report mere grammatical or wording rewrites unless they replace an explicitly gendered term or structure.
- If no changes are needed, return an empty array: [].
- Do not include any additional fields.

Content to review:

{{content}}
