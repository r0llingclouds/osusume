"""
Gradio front‑end for Osusume with integrated cover‑art + description cards.
Run with: python -m ui.gradio_app
"""

import re
from typing import NamedTuple
import gradio as gr
from service import get_recommendations
from src.anilist_query_searcher import search_anime

# Intro text
INTRO = (
    "## Osusume – AI‑powered anime recommender  \n"
    "Describe what you feel like watching and press **Recommend**.  \n"
    "_Examples_:  \n"
    "• I want an isekai anime with some comedy  \n"
    "• Give me something like Ghost in the Shell  \n"
    "• A dark fantasy from 2020"
)

# Regex to capture title and description from each bulleted line
RE_LINE = re.compile(r"^(?P<idx>\d+)\.\s*(?:\*([^*]+)\*|([^–—\-]+))\s*[–—\-]\s*(?P<desc>.+)$")

class Recommendation(NamedTuple):
    title: str
    desc: str


def parse_recommendations(markdown_text: str) -> list[Recommendation]:
    """
    Convert raw Markdown output into a list of Recommendation(title, desc).
    Supports lines like:
      1. *Title* – justification text
      2. Title – justification text
    """
    recs = []
    for line in markdown_text.splitlines():
        m = RE_LINE.match(line)
        if not m:
            continue
        # Title may be in group 2 (asterisk) or group 3 (plain)
        title_raw = m.group(2) or m.group(3)
        title = title_raw.strip()
        desc = m.group('desc').strip()
        recs.append(Recommendation(title, desc))
    return recs


def recommend_cb(query: str) -> str:
    """
    Returns HTML string rendering a flex‑box of cover + text cards.
    """
    q = query.strip()
    if not q:
        return "<p>⚠️ Please enter a request first.</p>"

    try:
        raw_md = get_recommendations(q)
    except Exception as e:
        return f"<p>❌ An error occurred: {e}</p>"

    recs = parse_recommendations(raw_md)
    if not recs:
        return "<p>⚠️ No recommendations found.</p>"

    # Build individual cards
    cards_html = []
    for rec in recs:
        # Fetch cover image URL
        try:
            hits = search_anime(search_term=rec.title, per_page=1)
            if hits:
                img_url = hits[0]['coverImage']['medium']
            else:
                img_url = 'https://via.placeholder.com/200x300?text=No+Image'
        except Exception:
            img_url = 'https://via.placeholder.com/200x300?text=Error'

        card = f"""
        <div style="flex:0 0 200px; margin:10px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.2); overflow:hidden; background:#fff;">
          <img src="{img_url}" alt="{rec.title}" style="width:100%; height:auto; object-fit:cover;"/>
          <div style="padding:8px;">
            <h4 style="margin:0 0 4px; font-size:1rem;">{rec.title}</h4>
            <p style="margin:0; font-size:0.85rem; color:#333;">{rec.desc}</p>
          </div>
        </div>
        """
        cards_html.append(card)

    # Wrap cards in a flex container
    html = f"""
    <div style="display:flex; flex-wrap:wrap; justify-content:center;">
      {''.join(cards_html)}
    </div>
    """
    return html

# Gradio UI
with gr.Blocks(title="Osusume") as demo:
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

    card_output = gr.HTML()

    btn.click(fn=recommend_cb, inputs=inp, outputs=card_output)
    inp.submit(fn=recommend_cb, inputs=inp, outputs=card_output)

if __name__ == '__main__':
    demo.launch(server_port=7860)
