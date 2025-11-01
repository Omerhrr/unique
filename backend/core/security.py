
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
                "language_code": "en"
            },

            "start_param": "dev_referral_code" 
        }

    if not telegram_data:
        raise HTTPException(status_code=401, detail="telegram-data header is missing.")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not configured.")

    authenticator = Authenticator(bot_token)
    try:

        validated_object: InitialData = authenticator.get_initial_data(telegram_data)


        if hasattr(validated_object, 'start_param') and validated_object.start_param:

            user_dict['referral_code_used'] = validated_object.start_param

        return {"user": user_dict}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
