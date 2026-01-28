
import streamlit as st
import os
from datetime import datetime
import threading

# --- Configuration ---
st.set_page_config(
    page_title="Blog Feature Preview",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Mock Data Generation ---
# In a real app, these would be Markdown files in a 'posts/' directory
def get_mock_posts():
    posts = []
    categories = ["Financial Independence", "Investing", "Lifestyle", "Budgeting"]
    for i in range(1, 21):
        posts.append({
            "id": i,
            "title": f"Lesson {i}: The Journey to Financial Freedom",
            "date": f"2025-{12 - (i%12) or 12:02d}-{28 - i:02d}",
            "author": "Duane Elverum",
            "category": categories[i % len(categories)],
            "excerpt": f"In this post, we explore the critical importance of step {i} in your financial roadmap. It's not just about the numbers...",
            "content": f"""
### The Importance of Step {i}

Financial freedom isn't built in a day. It takes consistent effort and smart decision making.

*   **Save aggressively:** Aim for a high savings rate.
*   **Invest wisely:** Low cost index funds are your friend.
*   **Live intentionally:** Spend on what brings you joy, cut the rest.

This is the full content of blog post number {i}. We can include charts, code snippets, and images here as well since it supports Markdown!

> "The best time to plant a tree was 20 years ago. The second best time is now."

#### Key Takeaways
1. Start now.
2. Be consistent.
3. Review your progress.
            """
        })
    # Sort by date descending
    return sorted(posts, key=lambda x: x['date'], reverse=True)

# --- UI Components ---
def render_blog_card(post):
    """Renders a preview card for a blog post."""
    with st.container():
        # Card styling handled by native Streamlit layout + some markdown
        col_img, col_text = st.columns([1, 4])
        
        with col_img:
            # Placeholder for a thumbnail
            st.markdown(f"""
            <div style="
                background-color: #f0f2f6; 
                height: 100px; 
                border-radius: 8px; 
                display: flex; 
                align-items: center; 
                justify-content: center;
                font-size: 30px;
            ">
                📝
            </div>
            """, unsafe_allow_html=True)
            
        with col_text:
            st.subheader(post["title"])
            st.caption(f"📅 {post['date']} • 🏷️ {post['category']} • ✍️ {post['author']}")
            st.write(post["excerpt"])
            
            if st.button(f"Read Post #{post['id']}", key=f"btn_{post['id']}", use_container_width=False):
                st.session_state["selected_post"] = post
                st.rerun()
        
        st.divider()

def render_full_post(post):
    """Renders the full blog post view."""
    if st.button("← Back to All Posts"):
        del st.session_state["selected_post"]
        st.rerun()
        
    st.title(post["title"])
    st.caption(f"Published on {post['date']} in {post['category']}")
    
    st.markdown("---")
    st.markdown(post["content"])
    st.markdown("---")
    
    # Example helper/CTA
    st.info("💡 **Enjoyed this article?** Check out the 'What If' simulator to apply these lessons to your own finances!")

# --- Main App ---
def main():
    # Custom CSS similar to your main app
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; }
        button[kind="primary"] { background-color: #0068c9 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    st.title("The Retirement Dashboard (Demo + Blog)")
    
    # Simulate the Tabs from your main app, adding 'Blog'
    tabs = st.tabs([
        "⛰️ The Big Picture", 
        "⏳ How Long Will It Last?",
        "📰 Blog",  # <-- The New Tab
        "🚀 What If?",
        "👤 Profile",
        "💰 Budget"
    ])
    
    # 1. Other tabs (Placeholders for context)
    with tabs[0]:
        st.info("This is your existing dashboard content...")
    
    # 2. Blog Tab
    with tabs[2]:
        if "selected_post" in st.session_state:
            render_full_post(st.session_state["selected_post"])
        else:
            st.header("Latest Updates & Financial Wisdom")
            
            # Simple Filter/Search
            col_search, col_cat = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Search posts...", placeholder="Search by title or keyword")
            with col_cat:
                category_filter = st.selectbox("Category", ["All", "Financial Independence", "Investing", "Lifestyle", "Budgeting"])
            
            posts = get_mock_posts()
            
            # Filter Logic
            filtered_posts = [
                p for p in posts 
                if (search_query.lower() in p['title'].lower() or search_query.lower() in p['excerpt'].lower())
                and (category_filter == "All" or p['category'] == category_filter)
            ]
            
            if not filtered_posts:
                st.warning("No posts found matching your criteria.")
            
            # Render Grid of Cards
            for post in filtered_posts:
                render_blog_card(post)

if __name__ == "__main__":
    main()
