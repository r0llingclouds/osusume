"""
Gradio front‑end for Osusume.
Run with:  python -m ui.gradio_app
"""

import gradio as gr
from service import get_recommendations

INTRO = (
    "## Osusume – AI‑powered anime recommender  \n"
    "Describe what you feel like watching and press **Recommend**.  \n"
    "_Examples_:  \n"
    "• *I want an isekai anime with some comedy*  \n"
    "• *Give me something like Ghost in the Shell*  \n"
    "• *A dark fantasy from 2020*"
)

def recommend_cb(query: str) -> str:
    """Gradio callback → CrewAI → Markdown string."""
    query = query.strip()
    if not query:
        return "⚠️ Please enter a request first."
    try:
        return get_recommendations(query)
    except Exception as exc:                     # noqa: BLE001
        # Convert stack‑trace into user‑friendly message
        return f"❌ An error occurred: `{exc}`"

with gr.Blocks(title="Osusume") as demo:
    gr.Markdown(INTRO)
    with gr.Row():
        inp = gr.Textbox(
            label="Your request",
            placeholder="I want an anime like Akira",
            scale=4,
            lines=1,
            autofocus=True,
        )
        btn = gr.Button("Recommend", variant="primary")
    out = gr.Markdown()

    btn.click(fn=recommend_cb, inputs=inp, outputs=out)
    inp.submit(fn=recommend_cb, inputs=inp, outputs=out)   # Enter key works too

if __name__ == "__main__":
    demo.launch(server_port=7860)