import requests
import os

def get_redgifs_temp_token():
    """Get a temporary token from RedGifs API"""
    url = "https://api.redgifs.com/v2/auth/temporary"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['token']
    except requests.RequestException as e:
        print(f"Error getting token: {e}")
        return None

def download_redgifs_dp(username, token):
    """Download profile picture using RedGifs API"""
    url = f"https://api.redgifs.com/v2/users/{username}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Authorization': f'Bearer {token}'
    }
    
    try:
        # Get user profile data
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        # Extract profile image URL
        profile_image_url = user_data.get('user', {}).get('profileImageUrl')
        
        if not profile_image_url:
            print("No profile picture found for this user")
            return None
            
        # Download the image
        image_response = requests.get(profile_image_url, headers=headers)
        image_response.raise_for_status()
        
        # Determine filename
        filename = f"{username}_profile.jpg"
        
        # Save the image
        with open(filename, 'wb') as f:
            f.write(image_response.content)
            
        print(f"Profile picture downloaded successfully as {filename}")
        return os.path.abspath(filename)
        
    except requests.RequestException as e:
        print(f"Error downloading profile picture: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def main():
    username = "emmabelovedxo"
    token = get_redgifs_temp_token()
    
    if token:
        download_redgifs_dp(username, token)
    else:
        print("Failed to obtain authentication token")

if __name__ == "__main__":
    main()
