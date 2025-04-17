"""
Gradio front‑end for Osusume with horizontal cover‑art + description cards (white text).
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

# Regex to capture title and description from each numbered line
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
        title_raw = m.group(2) or m.group(3)
        title = title_raw.strip()
        desc = m.group('desc').strip()
        recs.append(Recommendation(title, desc))
    return recs


def recommend_cb(query: str) -> str:
    """
    Returns HTML string rendering horizontal cards: white text on dark theme.
    """
    q = query.strip()
    if not q:
        return "<p style='color:white;'>⚠️ Please enter a request first.</p>"

    try:
        raw_md = get_recommendations(q)
    except Exception as e:
        return f"<p style='color:white;'>❌ An error occurred: {e}</p>"

    recs = parse_recommendations(raw_md)
    if not recs:
        return "<p style='color:white;'>⚠️ No recommendations found.</p>"

    cards_html = []
    for rec in recs:
        # Fetch cover image URL or placeholder
        try:
            hits = search_anime(search_term=rec.title, per_page=1)
            img_url = hits[0]['coverImage']['medium'] if hits else 'https://via.placeholder.com/200x300?text=No+Image'
        except Exception:
            img_url = 'https://via.placeholder.com/200x300?text=Error'

        # Build horizontal card HTML with white text
        card = f"""
        <div style="display:flex; flex-direction:row; width:90%; max-width:800px; margin:20px auto; "
                   "border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.2); overflow:hidden; background:#111;">
          <div style="flex:1; padding:16px; color:white;">
            <h3 style="margin:0 0 8px; font-size:1.2rem; color:white;">{rec.title}</h3>
            <p style="margin:0; font-size:1rem; color:white;">{rec.desc}</p>
          </div>
          <img src="{img_url}" alt="{rec.title}" style="width:200px; height:auto; object-fit:cover;"/>
        </div>
        """
        cards_html.append(card)

    # Wrap cards vertically stacked
    html = f"""
    <div style="display:flex; flex-direction:column; align-items:center; gap:16px; padding-bottom:20px;">
      {''.join(cards_html)}
    </div>
    """
    return html

# Gradio UI
with gr.Blocks(
    title="Osusume",
    css="""
    /* Set overall background to match dark theme */
    body { background-color: #000; }
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

    card_output = gr.HTML()

    btn.click(fn=recommend_cb, inputs=inp, outputs=card_output)
    inp.submit(fn=recommend_cb, inputs=inp, outputs=card_output)

if __name__ == '__main__':
    demo.launch(server_port=7860)
