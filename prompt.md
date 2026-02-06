I need you to generate vocabulary data in CSV format for an educational vocabulary video generator.

For each word I provide, generate:
1. definition - A clear concise definition (1-2 sentences; use semicolons instead of commas)
2. example - A natural example sentence using the word in context
3. prompt_image_guideline - A SPECIFIC image description for AI image generation:
   - Describe ONE large centered object or scene (NOT tiny or distant)
   - Use concrete visual objects (NOT abstract concepts)
   - Focus on SIMPLE recognizable subjects that are easy to illustrate
   - The main subject should fill most of the frame
   - Avoid: tiny figures; distant views; complex scenes; multiple subjects

OUTPUT FORMAT (CSV):
word,definition,example,prompt_image_guideline,vocabulary_type,revision,target_revision

RULES:
- Do NOT use commas within any field - use semicolons instead
- Keep definitions educational and easy to understand
- Example sentences should be practical and memorable
- Image prompts must describe LARGE CENTERED simple objects
- vocabulary_type: GeneralEnglish (or: BusinessEnglish; AcademicEnglish; IELTS; TOEFL)
- revision: 1
- target_revision: 5

GENERATE CSV FOR THESE WORDS:
word1, word2, word3, word4, word5, word6, word7, word8, word9, word10

Generate ONLY the CSV output with header row. No explanations or additional text.
