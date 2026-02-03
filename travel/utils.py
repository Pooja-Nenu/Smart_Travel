# travel/utils.py
import numpy as np
import pickle
import os
import faiss  # FAISS library for fast similarity search
from PIL import Image, ImageOps, ImageEnhance  # Added ImageEnhance for sharpness
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

        with Image.open(image_path) as pil_img:
            # 1. Normalize orientation and convert to RGB
            pil_img = ImageOps.exif_transpose(pil_img)
            pil_img = pil_img.convert('RGB')
            
            # --- ACCURACY BOOST 1: Strong Sharpness ---
            # High sharpness (3.0) helps distinguish small facial details between siblings.
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(3.0) 
            
            image_array = np.array(pil_img, dtype=np.uint8)
            image_array = np.ascontiguousarray(image_array)

            # --- ACCURACY BOOST 2: Higher Detection Depth ---
            face_locations = face_recognition.face_locations(image_array, number_of_times_to_upsample=2, model="hog") 
            
            # --- ACCURACY BOOST 3: High Precision Fingerprinting ---
            # Increased jitters to 5. This creates a much more stable signature to avoid lookalike confusion.
            face_encodings = face_recognition.face_encodings(image_array, face_locations, model="large", num_jitters=5)

            existing_groups = FaceGroup.objects.filter(trip=photo.trip)
            group_list = list(existing_groups)
            
            faiss_index = None
            if group_list:
                dimension = 128 
                faiss_index = faiss.IndexFlatL2(dimension)
                encodings_list = [pickle.loads(g.representative_encoding) for g in group_list]
                faiss_index.add(np.array(encodings_list).astype('float32'))

            # Accuracy tracker for the final summary
            all_face_accuracies = []

            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                # Filter out noise or very small background faces
                if (bottom - top) < 40:
                    continue

                matched_group = None
                
                if faiss_index:
                    query_encoding = np.array([encoding]).astype('float32')
                    # --- FIX: Search ONLY for the absolute Best Match (k=1) ---
                    distances, indices = faiss_index.search(query_encoding, k=1)
                    
                    dist = distances[0][0]
                    idx = indices[0][0]
                    
                    if idx != -1:
                        actual_dist = np.sqrt(dist) 
                        accuracy_score = max(0, (1 - actual_dist) * 100)
                        
                        # --- FIX: Strict Threshold (0.40) ---
                        # This filters out friends/siblings who might be "close" but not identical.
                        if actual_dist <= 0.40:
                            matched_group = group_list[idx]
                            all_face_accuracies.append(accuracy_score)
                            print(f"  STRICT MATCH: Group {matched_group.id} matched with {accuracy_score:.2f}% confidence.")
                        else:
                            # If it's between 0.40 and 0.60, we treat it as "Unknown" for safety.
                            print(f"  REJECTED: Close match (Dist: {actual_dist:.4f}), but not strict enough. Creating new group.")

                if not matched_group:
                    # Create a new clean FaceGroup for this unique signature
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
                    
                    # New groups represent a 100% baseline for that person
                    all_face_accuracies.append(100.0)

                    # Update the local index so other faces in the same photo can match this new group
                    group_list.append(matched_group)
                    if faiss_index:
                        faiss_index.add(np.array([encoding]).astype('float32'))
                    else:
                        faiss_index = faiss.IndexFlatL2(128)
                        faiss_index.add(np.array([encoding]).astype('float32'))

                # Link face to the confirmed group
                PhotoFaceRelation.objects.create(photo=photo, face_group=matched_group)

            # --- FINAL SUMMARY BLOCK ---
            if all_face_accuracies:
                avg_accuracy = sum(all_face_accuracies) / len(all_face_accuracies)
                
                print("\n" + "█" * 60)
                print(f"  STRICT PROCESSING COMPLETE (Photo ID: {photo_id})")
                print(f"  Faces Identified: {len(all_face_accuracies)}")
                print(f"  AVERAGE ACCURACY: {avg_accuracy:.2f}%")
                
                if avg_accuracy >= 90.0:
                    print("  RESULT: ★ TARGET 90% ACHIEVED ★")
                else:
                    print(f"  RESULT: Accuracy is {avg_accuracy:.2f}% (Strict mode is active).")
                print("█" * 60 + "\n")
            
    except Exception as e:
        print(f"Error processing faces for photo {photo_id}: {e}")
        import traceback
        traceback.print_exc()