# News-AI-Agent For Telegram

# News AI Agent

This project provides an AI-powered news summarization tool optimized for platforms like Telegram. 
The agent reads raw news articles and generates **concise, professional, and neutral summaries** with flexible output styles.

## Features
- Generates 2–3 key bullet point summaries under 700 characters.
- Always ends with the source of the article.
- Maintains a clear, factual, journalistic tone.
- Supports multiple summarization modes:
  - **Brief Mode** – Very short highlights.
  - **Analytical Mode** – More detailed cause–effect summaries.
  - **Regional Focus Mode** – Emphasizes local impact.

## Prompt Template

```python
prompt_template = """
You are a professional news summarizer for an international audience. 
Your task is to condense the article titled "{article_title}" into a short, neutral, and highly-informative summary.

INSTRUCTIONS:
- Output only 2–3 bullet points.
- Each bullet must present one key fact, decision, or development from the article.
- Use clear, factual, journalistic language (avoid adjectives, opinions, or speculation).
- Prioritize the following in order: 
  1. Who/What happened, 
  2. Where/When it happened, 
  3. Why it matters (impact or consequence).
- The entire summary MUST be under 700 characters total.
- At the very end, append: "Source: {source}".
- Do not include any text before or after the bullet points.

ARTICLE TEXT:
{text}

SUMMARY:
"""
```

## Example Output

**Input (BBC article on climate talks):**
> Title: *UN Climate Summit Opens with Global Pledges*

**Output:**
- World leaders opened the UN Climate Summit in New York, calling for stronger action on emissions.  
- The U.S. and EU pledged billions in green investment, while developing nations demanded fairer commitments.  
- Source: BBC  

## Usage
1. Clone the repository.
2. Integrate the prompt template with your LLM (e.g., GPT, Groq, OpenAI, or other providers).
3. Provide `{article_title}`, `{text}`, and `{source}` dynamically from your scraper or dataset.
4. Deploy the summaries directly to your preferred platform (Telegram, Web App, Newsletter).

## License
MIT License. Free to use, modify, and distribute.
