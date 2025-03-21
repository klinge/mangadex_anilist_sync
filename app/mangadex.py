import requests
import time
import logging
from typing import Dict, List
from dotenv import load_dotenv, set_key
import os
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables once for the module
load_dotenv()

class MangaDexClient:
    """Handles interactions with the MangaDex API."""

    def __init__(self, log_level=logging.INFO):
        # Configure logger
        self._setup_logging(os.getenv("LOG_LEVEL", "INFO"))
        
        logger.info("Initializing MangaDexClient")
        # Set base URL for API requests
        self.base_url = os.getenv("MD_BASE_URL")
        # Get credentials from environment variables
        self.user_name = os.getenv("MD_USER_NAME")
        self.user_password = os.getenv("MD_USER_PASSWORD")
        self.client_id = os.getenv("MD_CLIENT_ID")
        self.client_secret = os.getenv("MD_CLIENT_SECRET")
        
        # Try to load tokens
        self.access_token = os.getenv("MD_ACCESS_TOKEN")
        self.refresh_token = os.getenv("MD_REFRESH_TOKEN")
        self.token_expiry = os.getenv("MD_TOKEN_EXPIRY")
        
        if self.token_expiry:
            self.token_expiry = float(self.token_expiry)
            logger.debug(f"Loaded token with expiry: {self.token_expiry}")
        
        # Ensure we have valid tokens
        self._ensure_valid_token()
        logger.info("MangaDexClient initialized successfully")

    def _setup_logging(self, log_level):
        """Set up logging configuration."""
        # Create handler if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        logger.setLevel(log_level)

    def _ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if necessary."""
        current_time = time.time()
        
        # If token is missing or expired (with 60 seconds buffer)
        if not self.access_token or not self.token_expiry or current_time > (self.token_expiry - 60):
            logger.info("Access token missing or expired")
            if self.refresh_token:
                logger.info("Attempting to refresh token")
                self._refresh_token()
            else:
                logger.info("No refresh token available, performing full authorization")
                self._authorize()
        else:
            logger.debug("Using existing valid token")

    def _save_tokens(self, token_data):
        """Save tokens to environment variables and .env file."""
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        # Calculate expiry time (current time + expires_in seconds)
        self.token_expiry = time.time() + token_data["expires_in"]
        
        logger.info(f"Received new token valid for {token_data['expires_in']} seconds")
        logger.debug(f"Token expiry set to: {self.token_expiry}")
        
        # Update environment variables
        os.environ["MD_ACCESS_TOKEN"] = self.access_token
        os.environ["MD_REFRESH_TOKEN"] = self.refresh_token
        os.environ["MD_TOKEN_EXPIRY"] = str(self.token_expiry)
        
        # Update .env file
        env_path = Path('..') / '.env'
        set_key(env_path, "MD_ACCESS_TOKEN", self.access_token)
        set_key(env_path, "MD_REFRESH_TOKEN", self.refresh_token)
        set_key(env_path, "MD_TOKEN_EXPIRY", str(self.token_expiry))
        logger.debug("Tokens saved to environment and .env file")

    def _authorize(self):
        """Get new tokens using username and password."""
        logger.info("Authorizing with username and password")
        post_data = {
            "grant_type": "password",
            "username": self.user_name,
            "password": self.user_password,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            logger.debug("Sending authorization request")
            response = requests.post(
                "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token",
                data=post_data
            )
            response.raise_for_status()
            token_data = response.json()
            logger.info("Authorization successful")
            self._save_tokens(token_data)
        except requests.exceptions.HTTPError as e:
            logger.error(f"Authorization failed: {e}")
            raise

    def _refresh_token(self):
        """Refresh the access token using the refresh token."""
        logger.info("Refreshing access token")
        post_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            logger.debug("Sending token refresh request")
            response = requests.post(
                "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect/token",
                data=post_data
            )
            response.raise_for_status()
            token_data = response.json()
            logger.info("Token refresh successful")
            self._save_tokens(token_data)
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Token refresh failed: {e}")
            logger.info("Falling back to full authorization")
            self._authorize()

    def get_followed_manga(self) -> List[Dict]:
        """Fetch the list of manga the user follows."""
        logger.info("Fetching followed manga")
        self._ensure_valid_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(self.base_url + "/user/follows/manga", headers=headers)
            response.raise_for_status()
            manga_list = response.json()["data"]
            logger.info(f"Successfully fetched {len(manga_list)} followed manga")
            return manga_list
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch followed manga: {e}")
            raise

    def get_read_chapters(self, manga_id: str) -> List[str]:
        """Fetch the list of read chapters for a specific manga."""
        logger.info(f"Fetching read chapters for manga ID: {manga_id}")
        self._ensure_valid_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(f"{self.base_url}/manga/{manga_id}/read", headers=headers)
            response.raise_for_status()
            chapters = [chap["chapter"] for chap in response.json()["data"]]
            logger.info(f"Successfully fetched {len(chapters)} read chapters")
            logger.debug(f"Read chapters: {chapters}")
            return chapters
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch read chapters: {e}")
            raise

    def get_reading_progress(self) -> Dict[str, str]:
        """Fetch reading progress for followed manga using API methods."""
        logger.info("Fetching reading progress for all followed manga")
        progress = {}
        followed_manga = self.get_followed_manga()
        
        for i, manga in enumerate(followed_manga):
            manga_id = manga["id"]
            title = manga["attributes"]["title"].get("en", "Unknown Title")
            logger.info(f"Processing manga {i+1}/{len(followed_manga)}: {title}")
            
            try:
                chapters = self.get_read_chapters(manga_id)
                latest_chapter = max(chapters, default="0")  # Latest read chapter
                progress[title] = latest_chapter
                logger.info(f"Latest read chapter for '{title}': {latest_chapter}")
            except Exception as e:
                logger.error(f"Error processing manga '{title}': {e}")
                progress[title] = "Error"
        
        logger.info(f"Completed fetching reading progress for {len(progress)} manga")
        return progress
