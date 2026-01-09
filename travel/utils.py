# travel/utils.py
import numpy as np
import pickle
import os
from PIL import Image, ImageOps  # ImageOps handles orientation
from .models import TripPhoto, FaceGroup, PhotoFaceRelation

def process_photo_faces(photo_id):
    # Import inside function to prevent Windows/Python 3.12 startup issues
    import face_recognition 
    
    try:
        photo = TripPhoto.objects.get(id=photo_id)
        image_path = photo.image.path
        
        if not os.path.exists(image_path):
            print(f"File not found: {image_path}")
            return

        # --- Aggressive Image Normalization ---
        with Image.open(image_path) as pil_img:
            # 1. Handle EXIF orientation (auto-rotate image)
            pil_img = ImageOps.exif_transpose(pil_img)
            
            # 2. Force convert to RGB (Fixes Alpha/Transparency/CMYK issues)
            # We do this regardless of current mode to be safe
            pil_img = pil_img.convert('RGB')
            
            # Print debug info to server log
            print(f"Processing photo {photo_id}: mode={pil_img.mode}, size={pil_img.size}, numpy={np.__version__}")
            
            # 3. Explicitly cast to uint8 (8-bit) array and ensure C-contiguity
            # dlib (used by face_recognition) requires contiguous memory
            image_array = np.ascontiguousarray(np.array(pil_img, dtype='uint8'))

        # Detect faces
        face_encodings = face_recognition.face_encodings(image_array)

        existing_groups = FaceGroup.objects.filter(trip=photo.trip)
        
        for encoding in face_encodings:
            matched_group = None
            for group in existing_groups:
                group_encoding = pickle.loads(group.representative_encoding)
                # Lower tolerance = stricter matching
                match = face_recognition.compare_faces([group_encoding], encoding, tolerance=0.5)
                
                if match[0]:
                    matched_group = group
                    break
            
            if not matched_group:
                matched_group = FaceGroup.objects.create(
                    trip=photo.trip,
                    representative_encoding=pickle.dumps(encoding)
                )
                existing_groups = FaceGroup.objects.filter(trip=photo.trip)

            PhotoFaceRelation.objects.create(photo=photo, face_group=matched_group)
            
    except Exception as e:
        print(f"Error processing faces for photo {photo_id}: {e}")