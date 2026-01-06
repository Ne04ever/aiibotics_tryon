import gradio as gr
import os
from wave import wani2v, nano_banana_edit, save_photo, save_video
from data_info import *

# Helper to get garment choices from the folder
def get_garment_choices():
    # Update "garments_folder" to your actual folder path
    folder = "data/garment" 
    if not os.path.exists(folder):
        return []
    # Only list files that have '_front' in the name
    return [f for f in os.listdir(folder) if "_front" in f]

def update_previews(selected_front_name):
    if not selected_front_name:
        return None, None
    
    folder = "data/garment"
    front_path = os.path.join(folder, selected_front_name)
    
    # Map front to rear filename
    rear_filename = selected_front_name.replace("_front", "_rear")
    rear_path = os.path.join(folder, rear_filename)
    
    # Check if rear exists, otherwise return None for the second image
    if not os.path.exists(rear_path):
        rear_path = None
        
    return front_path, rear_path

def flow(person_img, garment_name, progress=gr.Progress()):
    if not all([person_img, garment_name]):
        raise gr.Error("Person image and Garment selection are required")

    folder = "data/garment"
    garment_img_front = os.path.join(folder, garment_name)
    
    progress(0, desc="🔍 Preparing garment images...")

    # Logic to find the rear garment path
    rear_img = None 
    rear_filename = garment_name.replace("_front", "_rear")
    potential_rear_path = os.path.join(folder, rear_filename)
    
    if os.path.exists(potential_rear_path):
        progress(0.1, desc="🔍 Rear garment found. Generating rear view...")
        rear_img = nano_banana_edit(img_person=person_img, img_garment=potential_rear_path, prompt=prompt_img_rear)

    progress(0.2, desc="🎨 Generating front view...")
    front_img = nano_banana_edit(img_person=person_img, img_garment=garment_img_front, prompt=prompt_img_front)
    
    if not front_img:
        raise gr.Error("❌ Front image generation failed")

    progress(0.6, desc="🎬 Creating video...")
    video_url = wani2v(img=front_img, last_img=rear_img, prompt=prompt_vid)
    
    if not video_url:
        raise gr.Error("❌ Video generation failed")

    progress(0.9, desc="💾 Saving results...")
    save_photo(url=front_img, type="front")
    if rear_img:
        save_photo(url=rear_img, type="rear")

    saved_path = save_video(url=video_url)
    return saved_path

with gr.Blocks() as app:
    gr.Markdown("# Generate your video")

    with gr.Row():
        with gr.Column():
            input_img = gr.Image(label="Upload Person Photo", type="filepath")
            
            garment_dropdown = gr.Dropdown(
                choices=get_garment_choices(),
                label="Select Garment",
                value=None
            )
            
            # Side-by-side previews of the selected garment
            with gr.Row():
                front_preview = gr.Image(label="Front View", interactive=False)
                rear_preview = gr.Image(label="Rear View", interactive=False)

            generate_btn = gr.Button("Generate", variant="primary")

        with gr.Column():
            output_video = gr.Video(label="Result")

    # This is the critical fix:
    # 1. fn returns TWO values
    # 2. outputs is a LIST of TWO components
    garment_dropdown.change(
        fn=update_previews,
        inputs=[garment_dropdown],
        outputs=[front_preview, rear_preview] 
    )

    generate_btn.click(
        fn=flow,
        inputs=[input_img, garment_dropdown],
        outputs=[output_video],
    )





if __name__ == "__main__":
    cwd = os.path.dirname(os.path.abspath(__file__))
    app.launch(
        server_name="0.0.0.0",
        debug=True,
        show_error=True,
        allowed_paths=[cwd],
        server_port=7860,
        share=True
    )