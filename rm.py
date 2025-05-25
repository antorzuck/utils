import os

# Get the current directory
current_directory = os.getcwd()

# Loop through all files in the current directory
for filename in os.listdir(current_directory):
    # Check if the file has a .jpg or .mp4 extension
    if filename.endswith('.jpg') or filename.endswith('.mp4'):
        # Construct the full file path
        file_path = os.path.join(current_directory, filename)
        try:
            # Remove the file
            os.remove(file_path)
            print(f'Removed: {filename}')
        except Exception as e:
            print(f'Error removing {filename}: {e}')

