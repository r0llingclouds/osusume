import gradio as gr
from service import get_recommendations
import os
import base64

# Intro text parts
INTRO_TEXT = (
    "Describe what you feel like watching and press **Recommend**.  \n"
    "_Examples_:  \n"
    "• I want an isekai anime with some comedy  \n"
    "• Give me something like Ghost in the Shell  \n"
    "• A dark fantasy from 2020"
)

def recommend_cb(query: str) -> str:
    """
    Returns HTML string rendering horizontal cards: white text on dark theme.
    """
    q = query.strip()
    if not q:
        return "<p style='color:white;'>⚠️ Please enter a request first.</p>"

    try:
        recs = get_recommendations(q)
    except Exception as e:
        return f"<p style='color:white;'>❌ An error occurred: {e}</p>"

    if not recs:
        return "<p style='color:white;'>⚠️ No recommendations found.</p>"

    cards_html = []
    for rec in recs:
        title = rec.title
        desc = rec.description
        img_url = rec.image_url

        card = f"""
        <div style="display:flex; flex-direction:row; width:90%; max-width:800px; margin:20px auto; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.2); overflow:hidden; background:#111;">
          <div style="flex:1; padding:16px; color:white;">
            <h3 style="margin:0 0 8px; font-size:1.2rem; color:white;">{title}</h3>
            <p style="margin:0; font-size:1rem; color:white;">{desc}</p>
          </div>
          <img src="{img_url}" alt="{title}" style="width:200px; height:auto; object-fit:cover;"/>
        </div>
        """
        cards_html.append(card)

    html = f"""
    <div style="display:flex; flex-direction:column; align-items:center; gap:16px; padding-bottom:20px;">
      {''.join(cards_html)}
    </div>
    """
    return html

# Get logo as base64 for embedding
logo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "media", "logo.png"))
with open(logo_path, "rb") as f:
    logo_data = f.read()
    encoded_logo = base64.b64encode(logo_data).decode("utf-8")

# Custom header HTML with perfect alignment
header_html = f'''
<div style="display:flex; width:100%; align-items:flex-start; margin:0; padding:0;">
    <div style="flex:3; margin:0; padding:0;">
        <h1 style="margin:0; padding:0; font-size:28px; line-height:1.2;">Osusume – AI‑powered anime recommender</h1>
        <p style="margin-top:6px; margin-bottom:0; padding:0;">Describe what you feel like watching and press <strong>Recommend</strong>.</p>
        <p style="margin-top:10px; margin-bottom:3px; padding:0;"><em>Examples:</em></p>
        <ul style="margin:0; padding-left:20px;">
            <li style="margin:0; padding:0;">I want an isekai anime with some comedy</li>
            <li style="margin:0; padding:0;">Give me something like Ghost in the Shell</li>
            <li style="margin:0; padding:0;">A dark fantasy from 2020</li>
        </ul>
    </div>
    <div style="flex:2; margin:0; padding:0; display:flex; justify-content:flex-end;">
        <img src="data:image/png;base64,{encoded_logo}" style="height:auto; width:450px; margin:0; padding:0; object-fit:contain;">
    </div>
</div>
'''

# Gradio UI
with gr.Blocks(
    title="Osusume",
    css="""
    /* Set overall background to match dark theme */
    body { background-color: #000; }
    
    /* Make sure content is aligned properly */
    .gradio-container {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Custom header styling */
    .custom-header {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
    }
    
    /* Request box position */
    .request-box {
        margin-top: 20px !important;
    }
    """
) as demo:
    # Custom HTML header with perfect alignment
    gr.HTML(header_html, elem_classes=["custom-header"])
    
    with gr.Row(elem_classes=["request-box"]):
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
