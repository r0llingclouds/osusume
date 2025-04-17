"""
Gradio front‑end for Osusume with cover‑art gallery.
Run with: python -m ui.gradio_app
"""

import re
import gradio as gr
from service import get_recommendations
from src.anilist_query_searcher import search_anime

# Intro Markdown
INTRO = (
    "## Osusume – AI‑powered anime recommender  \n"
    "Describe what you feel like watching and press **Recommend**.  \n"
    "_Examples_:  \n"
    "• I want an isekai anime with some comedy  \n"
    "• Give me something like Ghost in the Shell  \n"
    "• A dark fantasy from 2020"
)

# Title extraction: support Markdown asterisks or plain text before dash
ASTERISK_TITLE_RE = r"^\d+\.\s*\*([^*]+)\*"
PLAIN_TITLE_RE    = r"^\d+\.\s*([^–—\-]+)"


def extract_titles(markdown_text: str) -> list[str]:
    """
    Parse recommendation Markdown for titles. Supports two formats:
    1) *Title* → Markdown bold
    2) Plain Title – hint (captures text before dash)
    Returns list of titles in order.
    """
    lines = markdown_text.splitlines()
    titles = []
    for line in lines:
        # Try asterisk syntax first
        m = re.match(ASTERISK_TITLE_RE, line)
        if m:
            titles.append(m.group(1).strip())
            continue
        # Fallback: plain text up to dash
        m2 = re.match(PLAIN_TITLE_RE, line)
        if m2:
            titles.append(m2.group(1).strip())
    return titles


def recommend_cb(query: str) -> tuple[list[tuple[str, str]], str]:
    """
    Returns list of (cover_url, title) for gallery + raw Markdown text.
    """
    q = query.strip()
    if not q:
        return [], "⚠️ Please enter a request first."

    # 1) LLM Markdown recommendations
    try:
        raw_md = get_recommendations(q)
    except Exception as e:
        return [], f"❌ An error occurred: {e}"

    # 2) Extract titles and fetch cover images
    titles = extract_titles(raw_md)
    gallery_items: list[tuple[str, str]] = []
    for title in titles:
        try:
            hits = search_anime(search_term=title, per_page=1)
            if hits:
                url = hits[0]["coverImage"]["medium"]
                gallery_items.append((url, title))
            else:
                # placeholder if no hits
                gallery_items.append(("https://via.placeholder.com/150?text=No+Image", title))
        except Exception:
            gallery_items.append(("https://via.placeholder.com/150?text=Error", title))

    return gallery_items, raw_md

# Gradio UI setup
with gr.Blocks(
    title="Osusume",
    css="""
    /* Round and shadow gallery images */
    #cover-gallery img {
        border-radius: 0.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        object-fit: cover;
    }
    /* Hide gallery if no items */
    .gradio-gallery.empty { display: none; }
    """
) as demo:
    gr.Markdown(INTRO)

    with gr.Row():
        inp = gr.Textbox(
            label="Your request",
            placeholder="I want an anime like Akira",
            scale=4,
            lines=1,
            autofocus=True
        )
        btn = gr.Button("Recommend", variant="primary")

    gallery = gr.Gallery(
        label="Recommendations",
        columns=5,
        elem_id="cover-gallery"
    )
    out_md = gr.Markdown()

    btn.click(
        fn=recommend_cb,
        inputs=inp,
        outputs=[gallery, out_md]
    )
    inp.submit(
        fn=recommend_cb,
        inputs=inp,
        outputs=[gallery, out_md]
    )

if __name__ == "__main__":
    demo.launch(server_port=7860)
