from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

# โหลด BLIP Model ครั้งเดียว
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

def caption_image(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        output = model.generate(**inputs)
        caption = processor.decode(output[0], skip_special_tokens=True)

    return caption
