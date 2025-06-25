import os

def get_active_season():
    try:
        with open("active_season.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "2024/25"
