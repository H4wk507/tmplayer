def format_time(seconds: int) -> str:
    """Format time in seconds to a string."""
    hours = seconds // 3600
    seconds = seconds % 3600
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"
