import os

# Base directory for the project's data assets (this keeps paths portable)
BASE = os.path.join(os.path.dirname(__file__), "data")

#prompt for edited image of a person
prompt_img_front = "Full-body front-view image of a person wearing the dress. The person is in a neutral position, hands relaxed and standing straight"
prompt_img_rear = "Full-body rear-view image of a person wearing the dress. The person is in a neutral position, hands relaxed and standing straight"

#prompt for generating a video of a person
prompt_vid = "A person slowly rotates 180 degrees on their vertical axis against a clean studio background. The camera remains fixed in position capturing a front-facing view. The person begins facing the camera and smoothly rotates clockwise, revealing their side profile, back, and garments from all angles. The rotation is continuous and even-paced. Professional studio lighting remains constant. The person maintains their pose and posture throughout the entire rotation. High-quality, photorealistic rendering with consistent focus."

