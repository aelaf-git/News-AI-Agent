# agent_logic.py

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
import telegram
import asyncio

# --- 1. CORE SCRAPING FUNCTIONS ---

def get_latest_articles(site_url, link_selector):
    """
    Fetches the latest article links from a news homepage, with better filtering.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        # BUG FIX: Increased timeout for better reliability with international sites.
        response = requests.get(site_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        for link_element in soup.select(link_selector):
            title = link_element.get_text(strip=True)
            href = link_element.get('href')
            
            if title and href and len(title.split()) > 5:
                if href not in [a['url'] for a in articles]:
                    full_url = urljoin(site_url, href)
                    articles.append({'title': title, 'url': full_url})
                
        return articles[:10]

    except requests.RequestException as e:
        print(f"Error fetching homepage {site_url}: {e}")
        return []

def scrape_article_content(article_url):
    """
    Scrapes the main text and lead image from a single article page.
    
    Returns:
        A dictionary with 'text' and 'image_url'.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        paragraphs = soup.find_all('p')
        article_text = " ".join([p.get_text(strip=True) for p in paragraphs])

        image_url = None
        og_image = soup.find('meta', property='og_image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
        
        if not article_text:
            return None

        return {'text': article_text, 'image_url': image_url}

    except requests.RequestException as e:
        print(f"Error scraping article {article_url}: {e}")
        return None

# --- 2. SUMMARIZATION WITH LANGCHAIN + GROQ ---
def summarize_article(groq_api_key, article_text, article_title):
    """
    Summarizes the article with crash handling and a stricter length prompt.
    """
    if not article_text: return "Summary could not be generated."
    
    docs = [Document(page_content=article_text)]
    llm = ChatGroq(model_name="llama3-70b-8192", groq_api_key=groq_api_key, temperature=0.5)
    
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
- At the very end, mention the source.
- Do not include any text before or after the bullet points.

ARTICLE TEXT:
{text}

SUMMARY:
"""
    prompt = PromptTemplate(template=prompt_template, input_variables=["text", "article_title"])
    
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
    
    try:
        summary = chain.invoke({"input_documents": docs, "article_title": article_title})
        return summary['output_text']
    except Exception as e:
        print(f"Error during summarization with Groq API: {e}")
        return None

# --- 3. TELEGRAM POSTER & STATE MANAGEMENT ---
async def post_to_telegram(bot_token, channel_id, summary, article):
    """
    Formats and sends the message, truncating the summary if it's too long for a caption.
    """
    bot = telegram.Bot(token=bot_token)
    
    MAX_SUMMARY_LENGTH = 850
    
    if len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[:MAX_SUMMARY_LENGTH] + "..."

    message = f"📰 *{article['title']}*\n\n{summary}\n\n🔗 [Read the full article here]({article['url']})"

    try:
        if article.get('image_url'):
            await bot.send_photo(chat_id=channel_id, photo=article['image_url'], caption=message, parse_mode='Markdown')
        else:
            await bot.send_message(chat_id=channel_id, text=message, parse_mode='Markdown')
            
        print(f"Successfully posted '{article['title']}' to Telegram.")
        return True
    except Exception as e:
        print(f"Failed to post to Telegram: {e}")
        return False

def has_been_posted(article_url, file_path="posted_articles.txt"):
    if not os.path.exists(file_path): return False
    with open(file_path, 'r') as f:
        return article_url in f.read().splitlines()

def mark_as_posted(article_url, file_path="posted_articles.txt"):
    with open(file_path, 'a') as f:
        f.write(f"{article_url}\n")
