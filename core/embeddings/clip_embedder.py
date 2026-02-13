import torch
import open_clip
from PIL import Image
from typing import List


class CLIPEmbeddingGenerator:
    def __init__(self):
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k"
        )

        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")

    def embed_images(self, image_paths: List[str]):
        embeddings = []

        for path in image_paths:
            image = Image.open(path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)

            embeddings.append(image_features.cpu().numpy()[0])

        return embeddings

    def embed_text(self, texts: List[str]):
        text_tokens = self.tokenizer(texts).to(self.device)

        with torch.no_grad():
            text_features = self.model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()
