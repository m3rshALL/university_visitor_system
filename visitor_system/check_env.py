import os
from dotenv import load_dotenv

# Load .env.local file
load_dotenv('.env.local')

# Print environment variables
print(f"POSTGRES_HOST={os.getenv('POSTGRES_HOST')}")
print(f"POSTGRES_DB={os.getenv('POSTGRES_DB')}")
print(f"POSTGRES_USER={os.getenv('POSTGRES_USER')}")
print(f"DJANGO_SETTINGS_MODULE={os.getenv('DJANGO_SETTINGS_MODULE')}")
