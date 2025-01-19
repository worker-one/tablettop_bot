import base64
import io
import os

from PIL import Image


def image_to_base64(image: Image) -> str:
    """
    Converts a PIL Image to a base64 string.

    Args:
        image (Image): The image to convert.

    Returns:
        str: Base64 encoded string of the image.
    """
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")  # or any other format
    return base64.b64encode(buffered.getvalue()).decode()


def download_file_on_disk(bot, file_id: str, file_path: str) -> None:
    """
    Downloads a file from Telegram servers and saves it to the specified path.

    Args:
        bot: The Telegram bot instance.
        file_id: The unique identifier for the file to be downloaded.
        file_path: The local path where the downloaded file will be saved.
    """
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "wb") as file:
        file.write(downloaded_file)


def download_file_in_memory(bot, file_id: str) -> io.BytesIO:
    """
    Downloads a file from Telegram servers and parses it without saving it locally.

    Args:
        bot: The Telegram bot instance.
        file_id: The unique identifier for the file to be downloaded.

    Returns:
        io.BytesIO: The file object containing the downloaded file.
    """
    file_info = bot.get_file(file_id)
    downloaded_file: bytes = bot.download_file(file_info.file_path)

    # Convert bytes to a BytesIO object
    file_object = io.BytesIO(downloaded_file)

    return file_object


def create_keyfile_dict() -> dict[str, str]:
    """Create a dictionary with keys for the Google API from environment variables
    Returns:
        Dictionary with keys for the Google API
    Raises:
        ValueError: If any of the environment variables is not set
    """
    variables_keys = {
        "type": os.getenv("TYPE"),
        "project_id": os.getenv("PROJECT_ID"),
        "private_key_id": os.getenv("PRIVATE_KEY_ID"),
        "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("CLIENT_EMAIL"),
        "client_id": os.getenv("CLIENT_ID"),
        "auth_uri": os.getenv("AUTH_URI"),
        "token_uri": os.getenv("TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
    }
    for key, _ in variables_keys.items():
        if variables_keys[key] is None:
            raise ValueError(f"Environment variable {key} is not set")
    return variables_keys
