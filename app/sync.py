import os
from dotenv import load_dotenv
from mangadex import MangaDexClient
#from anilist import AniListClient

load_dotenv()


class SyncManager:
    """Manages the synchronization between MangaDex and AniList."""

    def __init__(self, md_client: MangaDexClient):
        self.md_client = md_client
        #self.al_client = al_client

    def sync(self):
        """Fetch progress from MangaDex and update AniList."""
        try:
            progress = self.md_client.get_reading_progress()
            """for title, chapter in progress.items():
                try:
                    media_id = self.al_client.get_media_id(title)
                    self.al_client.update_progress(media_id, chapter)
                    print(f"Updated {title} to chapter {chapter} on AniList")
                except Exception as e:
                    print(f"Failed to sync {title}: {e}")"""
        except Exception as e:
            print(f"Error fetching MangaDex progress: {e}")


def main():
    # Initialize clients with credentials from .env
    md_client = MangaDexClient()
    #al_client = AniListClient(access_token=os.getenv("AL_TOKEN"))

    # Set up and run the sync manager
    sync_manager = SyncManager(md_client)
    sync_manager.sync()


if __name__ == "__main__":
    main()