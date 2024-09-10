import requests
import json
import os
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Joplin API base URL
JOPLIN_API_URL = "http://127.0.0.1:41184"
TOKEN_FILE = "joplin_token.txt"  # File to store the real token
POLL_INTERVAL = 2  # Time to wait between polling /auth/check (in seconds)

# Function to request the auth_token and poll for user acceptance
def get_joplin_token():
    logger.info("Checking if token file exists.")

    # Check if the token file already exists
    if os.path.exists(TOKEN_FILE):
        logger.info(f"Token file found at {TOKEN_FILE}, reading the token.")
        with open(TOKEN_FILE, 'r') as file:
            token = file.read().strip()
            logger.info("Token read successfully.")
            return token

    # Step 1: POST /auth to get the auth_token (client challenge token)
    logger.info("Token file not found. Requesting authorization from Joplin's /auth endpoint.")
    response = requests.post(f"{JOPLIN_API_URL}/auth")

    if response.status_code == 200:
        data = response.json()
        auth_token = data.get('auth_token')
        logger.info(f"Received auth_token: {auth_token}. Waiting for user acceptance in the Joplin app.")

        # Step 2: Poll GET /auth/check with the auth_token to check for user acceptance
        token = poll_for_real_token(auth_token)
        
        if token:
            logger.info("User accepted the request. Real token received.")
            # Save the real token to a file for later use
            with open(TOKEN_FILE, 'w') as file:
                file.write(token)
            logger.info(f"Real token saved to {TOKEN_FILE} for future use.")
            return token
        else:
            logger.error("User rejected the request or an error occurred.")
            raise Exception("Authorization failed.")
    else:
        logger.error(f"Error authenticating with Joplin: {response.status_code}, {response.text}")
        raise Exception(f"Error authenticating with Joplin: {response.status_code}, {response.text}")

# Function to poll the /auth/check endpoint to retrieve the real token
def poll_for_real_token(auth_token):
    logger.info("Polling /auth/check for user acceptance.")
    check_url = f"{JOPLIN_API_URL}/auth/check?auth_token={auth_token}"
    
    while True:
        response = requests.get(check_url)

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')

            if status == "accepted":
                token = data.get('token')
                logger.info("Authorization accepted. Real token received.")
                return token  # Return the real token
            elif status == "rejected":
                logger.error("Authorization rejected by the user.")
                return None  # Authorization was rejected
            else:
                logger.info("Waiting for user acceptance...")
                time.sleep(POLL_INTERVAL)  # Wait before polling again
        else:
            logger.error(f"Error polling /auth/check: {response.status_code}, {response.text}")
            return None

# Function to create a new note in Joplin
def create_joplin_note(title, body, notebook_id=None):
    logger.info("Starting note creation process.")

    # Get the real token (either from the file or by requesting authorization)
    token = get_joplin_token()
    logger.info("Token retrieved, proceeding to create a new note.")

    # Define the API endpoint with the real token
    url = f"{JOPLIN_API_URL}/notes?token={token}"

    # Payload for the new note
    payload = {
        "title": title,
        "body": body,
    }

    # If notebook_id is provided, add the note to that notebook
    if notebook_id:
        payload["parent_id"] = notebook_id
        logger.info(f"Adding note to notebook with ID: {notebook_id}")

    # Convert the payload to JSON
    headers = {
        "Content-Type": "application/json"
    }

    # Make the POST request to create the note
    logger.info(f"Sending POST request to create a note with title: '{title}'")
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        logger.info("Note created successfully!")
        return response.json()  # Returns the newly created note details
    else:
        logger.error(f"Error creating note: {response.status_code}, {response.text}")
        return None

# Usage example
note_title = "My Test Note"
note_body = "This is a note created programmatically via the Joplin API."

logger.info("Starting the script to create a new note.")
create_joplin_note(note_title, note_body)
