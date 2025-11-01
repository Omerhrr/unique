
from fastapi import Header, HTTPException
from telegram_webapps_authentication import Authenticator, InitialData
import os
from typing import Optional


def get_validated_data(
    telegram_data: Optional[str] = Header(None, alias="telegram-data")
) -> dict:
    """
    A FastAPI dependency that validates Telegram initData OR returns mock data
    if DEV_MODE is enabled.
    """
    if os.getenv("DEV_MODE") == "true":
        print("--- [DEV MODE] Bypassing authentication. Returning mock user data. ---")
        return {
            "user": {
                "id": 999999,
                "first_name": "Dev",
                "last_name": "User",
                "username": "dev_user",
                "language_code": "en",
                "referral_code_used": "dev_referral_code" # Add for testing
            }
        }

    if not telegram_data:
        raise HTTPException(status_code=401, detail="telegram-data header is missing.")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not configured.")

    authenticator = Authenticator(bot_token)
    try:
        validated_object: InitialData = authenticator.get_initial_data(telegram_data)

        # --- NEW AND IMPROVED FIX ---
        # Manually construct the user dictionary for maximum compatibility
        user_dict = {
            "id": validated_object.user.id,
            "first_name": validated_object.user.first_name,
            "last_name": validated_object.user.last_name,
            "username": validated_object.user.username,
            "language_code": validated_object.user.language_code,
        }

        # Now, safely check for and add the referral code if it exists
        if hasattr(validated_object, 'start_param') and validated_object.start_param:
            user_dict['referral_code_used'] = validated_object.start_param

        return {"user": user_dict}
        # --- END OF FIX ---

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

