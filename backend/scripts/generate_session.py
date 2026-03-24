"""
One-time script to generate a Telethon StringSession.
Run this manually and save the output as TELEGRAM_SESSION_STRING in .env

Usage:
    python scripts/generate_session.py

You will be asked for your phone number and the verification code.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = input("Enter API_ID: ").strip()
API_HASH = input("Enter API_HASH: ").strip()

with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
    session_string = client.session.save()
    print(f"\nYour session string (save as TELEGRAM_SESSION_STRING in .env):\n")
    print(session_string)
