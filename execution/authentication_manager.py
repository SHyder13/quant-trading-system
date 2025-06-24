# execution/authentication_manager.py

import requests
import time
from config.secrets import API_KEY, USERNAME

class AuthenticationManager:
    def __init__(self, base_url="https://api.topstepx.com/api"):
        self.base_url = base_url
        self.session_token = None
        self.token_expiry_time = 0
        self.session = requests.Session()

    def get_session_token(self):
        """Provides a valid session token, refreshing if necessary."""
        # Check if the token exists and is not expired (with a 5-minute buffer)
        if self.session_token and time.time() < self.token_expiry_time - 300:
            print("Using existing session token.")
            return self.session_token
        
        # If token is invalid or expiring soon, fetch a new one
        print("Fetching new session token...")
        return self._login()

    def _login(self):
        """Logs in to the API to retrieve a new session token."""
        endpoint = f"{self.base_url}/Auth/loginKey"
        payload = {
            "userName": USERNAME,
            "apiKey": API_KEY
        }
        print(f"--> Attempting login to {endpoint} with payload: {{'userName': '{USERNAME}', 'apiKey': '[REDACTED]'}}")

        headers = {
            'accept': 'text/plain',
            'Content-Type': 'application/json'
        }

        try:
            response = self.session.post(endpoint, headers=headers, json=payload)
            print(f"<-- API Response Status Code: {response.status_code}")
            print(f"<-- API Response Body: {response.text}")

            # Check for non-200 status codes first
            if response.status_code != 200:
                print(f"Authentication failed with status code: {response.status_code}")
                return None

            data = response.json()

            if data.get('success'):
                self.session_token = data['token']
                # Session tokens are valid for 24 hours (86400 seconds)
                self.token_expiry_time = time.time() + 86400
                print("Successfully authenticated and received session token.")
                return self.session_token
            else:
                error_msg = data.get('errorMessage', 'Unknown error')
                print(f"Authentication failed: {error_msg}")
                print(f"Full error response: {data}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Error during authentication request: {e}")
            return None
        except requests.exceptions.JSONDecodeError:
            print("Failed to decode JSON from response. The API might be down or returning non-JSON content.")
            return None
