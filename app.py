# app.py
import streamlit as st
import os
from dotenv import load_dotenv
import asyncio
import time
from datetime import datetime

# Import the core logic functions
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
NEWS_SITES = {
    # ... (The list of 30 news sites remains unchanged) ...
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
if 'site_index' not in st.session_state:
    st.session_state.site_index = 0
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []

def add_log(message):
    """Adds a timestamped message to the log."""
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_messages.insert(0, f"[{now}] {message}")
    # Keep the log from growing too large
    if len(st.session_state.log_messages) > 50:
        st.session_state.log_messages.pop()

# --- Sidebar Controls ---
st.sidebar.header("Agent Controls")

if st.sidebar.button("🚀 Start Agent", use_container_width=True):
    if not st.session_state.running:
        st.session_state.running = True
        st.session_state.site_index = 0
        add_log("Agent started.")

if st.sidebar.button("🛑 Stop Agent", use_container_width=True):
    if st.session_state.running:
        st.session_state.running = False
        add_log("Agent stopping...")

# Status indicator
if st.session_state.running:
    st.sidebar.success(f"Agent is running... (Processing site {st.session_state.site_index + 1})")
else:
    st.sidebar.info("Agent is stopped.")

st.sidebar.header("Media Configuration")
selected_sites = st.sidebar.multiselect(
    "Select or Exclude News Websites",
    options=list(NEWS_SITES.keys()),
    default=list(NEWS_SITES.keys())[:10]
)

# --- 3. MAIN AGENT LOOP ---

# Get API keys once
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Check for API keys before starting
if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID]):
    st.error("🚨 Missing API keys in your .env file! The agent cannot run.")
    st.session_state.running = False

if st.session_state.running:
    if not selected_sites:
        st.warning("No media sources selected. Please select at least one source.")
        st.session_state.running = False
    else:
        # Determine which site to process in this cycle
        # This ensures that even if the user changes the selection, we don't get an error
        current_index = st.session_state.site_index % len(selected_sites)
        site_name = selected_sites[current_index]
        config = NEWS_SITES[site_name]

        add_log(f"--- Checking {site_name} ---")

        # --- Run the core logic for one site ---
        latest_articles = get_latest_articles(config['url'], config['selector'])

        if not latest_articles:
            add_log(f"No articles found or site error for {site_name}.")
        else:
            new_articles_found = 0
            for article in latest_articles:
                if has_been_posted(article['url']):
                    continue # Skip silently to keep log clean

                new_articles_found += 1
                add_log(f"New article found: '{article['title'][:50]}...'")
                
                content = scrape_article_content(article['url'])
                if not content or not content['text']:
                    add_log(f"⚠️ Could not scrape content for article. Skipping.")
                    continue
                
                article['image_url'] = content['image_url']
                summary = summarize_article(GROQ_API_KEY, content['text'], article['title'])
                
                if not summary:
                    add_log(f"⚠️ Summarization failed. Skipping.")
                    continue
                
                success = asyncio.run(post_to_telegram(
                    TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, summary, article
                ))

                if success:
                    mark_as_posted(article['url'])
                    add_log(f"✅ Successfully posted '{article['title'][:50]}...'!")
                else:
                    add_log(f"❌ Failed to post article.")
            
            if new_articles_found == 0:
                add_log(f"No new articles to post from {site_name}.")

        # --- Move to the next site for the next cycle ---
        st.session_state.site_index += 1
        
        # Use Streamlit's rerun feature to create an immediate, continuous loop
        time.sleep(1) # A tiny sleep to prevent maxing out the CPU
        st.rerun()

# --- 4. DISPLAY LOGS ---
st.header("Activity Log")
log_container = st.container(height=500)
with log_container:
    for msg in st.session_state.log_messages:
        if "✅" in msg:
            st.success(msg)
        elif "⚠️" in msg or "❌" in msg:
            st.warning(msg)
        else:
            st.info(msg)
