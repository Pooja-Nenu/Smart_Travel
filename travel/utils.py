# travel/utils.py
import numpy as np
import pickle
import os
from PIL import Image, ImageOps  # ImageOps handles orientation
from .models import TripPhoto, FaceGroup, PhotoFaceRelation, FaceMergeSuggestion
from django.core.files.base import ContentFile
import io

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
            pil_img = pil_img.convert('RGB')
            
            # 3. Explicitly cast to uint8 array
            image_array = np.ascontiguousarray(np.array(pil_img, dtype='uint8'))

            # Detect faces - get BOTH locations and encodings
            # We use 'hog' for speed, but 'cnn' is more accurate (needs GPU/CPU power)
            face_locations = face_recognition.face_locations(image_array, model="hog")
            face_encodings = face_recognition.face_encodings(image_array, face_locations)

            existing_groups = FaceGroup.objects.filter(trip=photo.trip)
            
            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                # Only process faces that are large enough (filter out background noise)
                face_height = bottom - top
                if face_height < 40:
                    continue

                matched_group = None
                maybe_matches = []
                
                for group in existing_groups:
                    group_encoding = pickle.loads(group.representative_encoding)
                    
                    # Calculate actual distance to see how close it is
                    distance = face_recognition.face_distance([group_encoding], encoding)[0]

                    # 0.45 is strict - prevents "Lookalike" glitches
                    match = distance <= 0.45
                    
                    if match:
                        matched_group = group
                        break
                    
                    # If not a strict match, check if it's a "maybe" (0.65)
                    if distance <= 0.65:
                        maybe_matches.append(group)
                
                if not matched_group:
                    # Create a thumbnail crop for the new face group
                    padding = 50
                    img_h, img_w, _ = image_array.shape
                    
                    crop_top = max(0, top - padding)
                    crop_bottom = min(img_h, bottom + padding)
                    crop_left = max(0, left - padding)
                    crop_right = min(img_w, right + padding)
                    
                    face_crop = pil_img.crop((crop_left, crop_top, crop_right, crop_bottom))
                    face_crop.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    
                    thumb_io = io.BytesIO()
                    face_crop.save(thumb_io, format='JPEG', quality=95)
                    thumb_file = ContentFile(thumb_io.getvalue(), name=f"face_{photo.id}.jpg")

                    matched_group = FaceGroup.objects.create(
                        trip=photo.trip,
                        representative_encoding=pickle.dumps(encoding),
                        thumbnail=thumb_file
                    )
                    
                    # Create suggestions for all "maybe" matches
                    for maybe_group in maybe_matches:
                        FaceMergeSuggestion.objects.get_or_create(
                            trip=photo.trip,
                            group_a=maybe_group,
                            group_b=matched_group
                        )
                    
                    existing_groups = FaceGroup.objects.filter(trip=photo.trip)

                PhotoFaceRelation.objects.create(photo=photo, face_group=matched_group)
            
    except Exception as e:
        print(f"Error processing faces for photo {photo_id}: {e}")
        import traceback
        traceback.print_exc()