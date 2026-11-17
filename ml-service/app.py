import gradio as gr
from PIL import Image
from src.ocr_engine import OCREngine
from src.model_predictor import ErrorPredictor

# Initialize predictor
predictor = ErrorPredictor()

def diagnose_machine_error(input_image: Image.Image):
    """
    Core inference pipeline invoked by both the Gradio UI and the REST API.
    """
    if input_image is None:
        return "⚠️ Please upload or capture an image of the machine display.", None

    token_model, raw_token, ocr_info, annotated_image = OCREngine.process_frame(input_image, mirror=True)

    if not token_model:
        return f"❌ No error code detected.\n\n{ocr_info}", annotated_image

    try:
        cause, solution = predictor.predict(token_model)
        markdown_result = (
            f"### 🎯 Diagnostic Report\n\n"
            f"* **Detected Code:** `{raw_token}` (Normalized: `{token_model}`)\n\n"
            f"#### 📌 Root Cause:\n{cause}\n\n"
            f"#### 💡 Corrective Action / Solution:\n{solution}\n\n"
            f"---\n"
            f"🔍 *OCR Context: {ocr_info}*"
        )
    except Exception as e:
        markdown_result = f"⚠️ Inference failed for detected code `{raw_token}`: {e}"

    return markdown_result, annotated_image

# Gradio Interface Definition
title = "🏭 Smart Industry - Machine Error Diagnostic (Lessons Learned)"
description = (
    "Computer Vision & NLP assistant for shop-floor operators. "
    "Captures error codes from machine consoles, extracts tokens via multi-pass OCR, "
    "and predicts standard resolution procedures."
)

demo = gr.Interface(
    fn=diagnose_machine_error,
    inputs=[
        gr.Image(type="pil", label="📷 Error Display Photo / Webcam Stream")
    ],
    outputs=[
        gr.Markdown(label="Diagnostic & Lessons Learned"),
        gr.Image(label="Processed ROI & Detection Visualizer")
    ],
    title=title,
    description=description,
    allow_flagging="never",
    api_name="diagnose"  # Exposes REST endpoint: /api/diagnose
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
