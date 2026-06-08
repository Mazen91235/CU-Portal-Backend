from pgvector import Vector
import face_recognition
import numpy as np
from PIL import Image
from core.iServices.iAIService import IAIService
from core.entities.patientUser import PatientUser
from core.utils.stringHandler import StringHandler
from core.utils.fileHandler import FileHandler


class AIService(IAIService):
    def __init__(self) -> None:
        self.FACEMODEL = "hog"
        self.TOLERANCE = 0.8
        # Define the maximum bounding box for the image
        self.MAX_SIZE = (640, 480)

    def generate_embeddings(self, path):
        try:
            # 1. Load with PIL for high-quality resizing
            file_path = FileHandler.retrieve_file_path(path)
            pil_image = Image.open(file_path)

            # Ensure the image is in RGB format (handles PNGs with transparency or grayscale)
            pil_image = pil_image.convert("RGB")

            # 2. Resize dynamically: 'thumbnail' scales the image down to fit within MAX_SIZE
            # while maintaining aspect ratio. LANCZOS ensures high-quality downsampling.
            # pil_image.thumbnail(self.MAX_SIZE, Image.Resampling.LANCZOS)

            # Convert back to a numpy array for face_recognition
            image = np.array(pil_image)

        except Exception:
            return None

        # 3. First attempt: HOG model
        try:
            locations = face_recognition.face_locations(image, model=self.FACEMODEL)
        except Exception:
            locations = []

        # # 4. Fallback attempt: CNN model
        # if not locations:
        #     try:
        #         locations = face_recognition.face_locations(image, model="cnn")
        #     except Exception:
        #         return None

        # If both models fail to find a face
        if not locations:
            return None

        # Calculate bounding box area to find the dominant face
        dominant_location = max(
            locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3])
        )

        try:
            encodings = face_recognition.face_encodings(image, [dominant_location])
        except Exception:
            return None

        dominant_encoding = encodings[0] if encodings else None

        return Vector(dominant_encoding) if dominant_encoding is not None else None
