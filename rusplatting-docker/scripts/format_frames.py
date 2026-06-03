import sys
import os
import shutil

# Get the scene directory from the command line argument
scene_dir = sys.argv[1]
upscaled_dir = os.path.join(scene_dir, "upscaled")
final_images_dir = os.path.join(scene_dir, "images")

os.makedirs(final_images_dir, exist_ok=True)

files = sorted([f for f in os.listdir(upscaled_dir) if f.endswith('.jpg') or f.endswith('.png')])
real_frame_counter = 1

for i, filename in enumerate(files):
    source_path = os.path.join(upscaled_dir, filename)
    if i % 2 == 0:  
        new_name = f"frame{real_frame_counter:03d}.jpg"
        shutil.copy(source_path, os.path.join(final_images_dir, new_name))
    else:
        new_name = f"frame{real_frame_counter:03d}_to_frame{real_frame_counter+1:03d}.jpg"
        shutil.copy(source_path, os.path.join(final_images_dir, new_name))
        real_frame_counter += 1

print(f"Finished formatting frames for: {scene_dir}")
