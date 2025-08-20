# app.py
import streamlit as st
import os
from dotenv import load_dotenv
import asyncio
import time

# Import the core logic functions from your other file
from agent_logic import (
    get_latest_articles,
    scrape_article_content,
    summarize_article,
    post_to_telegram,
    has_been_posted,
    mark_as_posted
)

load_dotenv()

# --- 1. NEWS SOURCE CONFIGURATION ---
# A diverse list of 30 news sources from around the world.
# NOTE: Website structures change! These CSS selectors may need updating over time.
NEWS_SITES = {
    # North America
    "AP News": {"url": "https://apnews.com", "selector": ".CardHeadline > a"},
    "CNN": {"url": "https://www.cnn.com", "selector": "a[data-link-type='article']"},
    "NPR News": {"url": "https://www.npr.org/sections/news/", "selector": "h2.title > a"},
    "CBC (Canada)": {"url": "https://www.cbc.ca/news", "selector": "a.headline"},
    
    # Europe
    "BBC News (UK)": {"url": "https://www.bbc.com/news", "selector": "a.gs-c-promo-heading"},
    "The Guardian (UK)": {"url": "https://www.theguardian.com/international", "selector": ".dcr-card-headline > a"},
    "DW News (Germany)": {"url": "https://www.dw.com/en/top-stories/s-9097", "selector": "a.teaser-title-link"},
    "France 24 (France)": {"url": "https://www.france24.com/en/", "selector": "p.article__title > a"},
    "El País (Spain)": {"url": "https://english.elpais.com/", "selector": "h2.c_t > a"},
    
    # Russia
    "TASS (Russia)": {"url": "https://tass.com/", "selector": "a.tass_defaults_grid-row__title"},
    "RT (Russia)": {"url": "https://www.rt.com/", "selector": ".card-main__heading > a"},
    
    # Asia
    "Xinhua (China)": {"url": "http://www.xinhuanet.com/english/", "selector": "h3 > a"},
    "People's Daily (China)": {"url": "http://en.people.cn/", "selector": ".hd a"},
    "Al Jazeera": {"url": "https://www.aljazeera.com/", "selector": "a.u-clickable-card__link"},
    "Times of India (India)": {"url": "https://timesofindia.indiatimes.com/world", "selector": "a.w_img"},
    "The Japan Times (Japan)": {"url": "https://www.japantimes.co.jp/", "selector": "h3 > a"},
    "The Straits Times (Singapore)": {"url": "https://www.straitstimes.com/world", "selector": ".card-title > a"},
    
    # Africa
    "Premium Times (Nigeria)": {"url": "https://www.premiumtimesng.com/category/news/top-news", "selector": "h3 > a"},
    "Daily Maverick (S. Africa)": {"url": "https://www.dailymaverick.co.za/section/world/", "selector": "h1 > a"},
    "The East African (Kenya)": {"url": "https://www.theeastafrican.co.ke/", "selector": "h4 > a"},
    "Ahram Online (Egypt)": {"url": "https://english.ahram.org.eg/Category/2/World.aspx", "selector": "h3 > a"},

    # South America
    "Folha de S.Paulo (Brazil)": {"url": "https://www1.folha.uol.com.br/internacional/en/", "selector": "a.c-main-headline__url"},
    "Clarín (Argentina)": {"url": "https://www.clarin.com/mundo/", "selector": "h2 > a"},
    "El Tiempo (Colombia)": {"url": "https://www.eltiempo.com/mundo", "selector": "a.title-container"},

    # Australia & Oceania
    "ABC News (Australia)": {"url": "https://www.abc.net.au/news", "selector": "a[data-component='Link']"},
    "Sydney Morning Herald (Australia)": {"url": "https://www.smh.com.au/world", "selector": "h3 > a"},
    "RNZ (New Zealand)": {"url": "https://www.rnz.co.nz/news/world", "selector": "h3 > a"},

    # Business & Finance
    "CNBC (World)": {"url": "https://www.cnbc.com/world/", "selector": "a.Card-title"},
    "Bloomberg": {"url": "https://www.bloomberg.com/", "selector": "a[data-component='headline']"},
    "The Economist": {"url": "https://www.economist.com/", "selector": "a[data-analytics='hero-click']"},
}


# --- 2. STREAMLIT UI SETUP ---
st.set_page_config(page_title="Autonomous News Agent", layout="wide")
st.title("📰 Autonomous News Agent")
st.markdown("This agent autonomously scrapes news from global sources, summarizes new articles, and posts them to a Telegram channel.")

# Initialize session state for agent control
if 'running' not in st.session_state:
    st.session_state.running = False

# --- Sidebar Controls ---
st.sidebar.header("Agent Controls")

# Start and Stop buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🚀 Start Agent", use_container_width=True):
        st.session_state.running = True
with col2:
    if st.button("🛑 Stop Agent", use_container_width=True):
        st.session_state.running = False

# Status indicator
if st.session_state.running:
    st.sidebar.success("Agent is running...")
else:
    st.sidebar.info("Agent is stopped.")

st.sidebar.header("Media Configuration")
# Allow user to select which news sites to process
selected_sites = st.sidebar.multiselect(
    "Select or Exclude News Websites",
    options=list(NEWS_SITES.keys()),
    default=list(NEWS_SITES.keys())[:5] # Default to first 5 sites
)


# --- 3. MAIN AGENT LOOP ---
# This is the core autonomous logic.
# It runs only when the 'running' state is True.

if st.session_state.running:
    # Get API keys once
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

    # Check for API keys
    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID]):
        st.error("🚨 Missing API keys in your .env file! Please add them and restart.")
        st.session_state.running = False # Stop the agent if keys are missing
    else:
        # Create a placeholder for the agent's live output
        log_placeholder = st.empty()

        # The main autonomous loop
        while st.session_state.running:
            log_messages = []
            log_messages.append("--- Agent Run Started ---")
            log_placeholder.info("\n".join(log_messages))

            for site_name in selected_sites:
                if not st.session_state.running: # Check if stop was pressed during the run
                    break
                
                config = NEWS_SITES[site_name]
                log_messages.append(f"▶️ Processing {site_name}...")
                log_placeholder.info("\n".join(log_messages))

                latest_articles = get_latest_articles(config['url'], config['selector'])

                if not latest_articles:
                    log_messages.append(f"   - No articles found for {site_name}.")
                    log_placeholder.warning("\n".join(log_messages))
                    continue

                new_articles_posted = 0
                for article in latest_articles:
                    if not st.session_state.running: break

                    if has_been_posted(article['url']):
                        continue # Skip already posted articles quietly
                    
                    log_messages.append(f"   - Found new article: '{article['title'][:40]}...'")
                    log_placeholder.info("\n".join(log_messages))

                    # Scrape, Summarize, and Post
                    content = scrape_article_content(article['url'])
                    if not content or not content['text']:
                        log_messages.append(f"      - ⚠️ Could not scrape content. Skipping.")
                        log_placeholder.warning("\n".join(log_messages))
                        continue
                    
                    article['image_url'] = content['image_url']
                    summary = summarize_article(GROQ_API_KEY, content['text'], article['title'])
                    
                    if not summary:
                        log_messages.append(f"      - ⚠️ Could not summarize. Skipping.")
                        log_placeholder.warning("\n".join(log_messages))
                        continue
                    
                    success = asyncio.run(post_to_telegram(
                        TELEGRAM_BOT_TOKEN,
                        TELEGRAM_CHANNEL_ID,
                        summary,
                        article
                    ))

                    if success:
                        mark_as_posted(article['url'])
                        new_articles_posted += 1
                        log_messages.append(f"      - ✅ Successfully posted to Telegram!")
                        log_placeholder.success("\n".join(log_messages))
                    else:
                        log_messages.append(f"      - ❌ Failed to post to Telegram.")
                        log_placeholder.error("\n".join(log_messages))

                if new_articles_posted == 0:
                     log_messages.append(f"   - No new articles to post from {site_name}.")
                     log_placeholder.info("\n".join(log_messages))


            log_messages.append("\n--- Agent Run Finished. Waiting for 1 minute... ---")
            log_placeholder.info("\n".join(log_messages))
            
            # Wait for 60 seconds before the next run
            time.sleep(60)
            
else:
    st.info("Agent is currently stopped. Press 'Start Agent' in the sidebar to begin.")
