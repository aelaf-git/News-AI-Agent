# app.py
import streamlit as st
import os
from dotenv import load_dotenv
import asyncio

from agent_logic import (
    get_latest_articles,
    scrape_article_content,
    summarize_article,
    post_to_telegram,
    has_been_posted,
    mark_as_posted
)

load_dotenv()

# --- Streamlit UI ---
st.set_page_config(page_title="Website News Agent", layout="wide")
st.title("📰 Website to Telegram News Agent")
st.markdown("This agent scrapes the latest news from websites, summarizes it, and posts to Telegram.")

# --- Scraper Configuration ---
# This is where we define how to scrape each site.
# To add a new site, you need its homepage URL and the CSS selector for its headlines.
NEWS_SITES = {
    "BBC News": {
        "url": "https://www.bbc.com/news",
        "selector": "a.gs-c-promo-heading"  # This selector is specific to BBC headlines
    },
    "CNN": {
        "url": "https://www.cnn.com",
        "selector": "a[data-link-type='article']"  # This targets links specifically marked as articles
    },
    "Al Jazeera": {
        "url": "https://www.aljazeera.com/",
        "selector": "a.u-clickable-card__link"  # Targets the main clickable links on story cards
    },
    "The Guardian (World)": {
        "url": "https://www.theguardian.com/international",
        # This is more specific: targets links within an element with a 'dcr-card-headline' class
        "selector": ".dcr-card-headline > a"
    },
    "AP News": {
        "url": "https://apnews.com",
        # Targets the headline link inside a story card
        "selector": ".CardHeadline > a"
    },
    "CNBC (World)": {
        "url": "https://www.cnbc.com/world/",
        # Targets links with the 'Card-title' class name
        "selector": "a.Card-title"
    },
    "NPR News": {
        "url": "https://www.npr.org/sections/news/",
        # Targets the h2 title link within an article story container
        "selector": "h2.title > a"
    },
    "DW News": {
        "url": "https://www.dw.com/en/top-stories/s-9097",
        # Targets links inside a teaser component
        "selector": "a.teaser-title-link"
    },
    # REMOVED: Reuters, Politico, NYT - These sites have strong anti-scraping measures
    # that block simple requests, causing errors.
}

st.sidebar.header("Configuration")
selected_sites = st.sidebar.multiselect(
    "Select News Websites to Process",
    options=list(NEWS_SITES.keys()),
    default=list(NEWS_SITES.keys())
)

if st.button("🚀 Scrape, Summarize, and Post New Articles", use_container_width=True):
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID]):
        st.error("🚨 Missing API keys in your .env file!")
    else:
        st.info("Agent started! Checking for new articles...")
        
        for site_name in selected_sites:
            config = NEWS_SITES[site_name]
            st.write(f"--- Processing {site_name} ---")

            with st.spinner(f"Fetching latest articles from {site_name}..."):
                latest_articles = get_latest_articles(config['url'], config['selector'])

            if not latest_articles:
                st.write("No articles found or site could not be reached.")
                continue

            for article in latest_articles:
                if has_been_posted(article['url']):
                    st.write(f"✅ Skipping '{article['title']}' (already posted).")
                    continue

                st.write(f"Processing new article: '{article['title']}'")
                
                with st.spinner(f"Scraping content from article..."):
                    content = scrape_article_content(article['url'])
                
                if not content or not content['text']:
                    st.warning(f"Could not scrape content for '{article['title']}'. Skipping.")
                    continue
                
                # Add the scraped image url to our article dictionary
                article['image_url'] = content['image_url']

                with st.spinner(f"Summarizing article with Groq..."):
                    summary = summarize_article(GROQ_API_KEY, content['text'], article['title'])
                
                # If summarization failed (returned None), skip this article
                if not summary:
                    st.warning(f"Could not summarize '{article['title']}'. Skipping.")
                    continue
                
                with st.spinner(f"Posting to Telegram..."):
                    success = asyncio.run(post_to_telegram(
                        TELEGRAM_BOT_TOKEN,
                        TELEGRAM_CHANNEL_ID,
                        summary,
                        article
                    ))

                if success:
                    mark_as_posted(article['url'])
                    st.success(f"🎉 Successfully posted '{article['title']}'!")
                else:
                    st.error(f"❌ Failed to post '{article['title']}'.")

        st.success("Agent has finished its run!")