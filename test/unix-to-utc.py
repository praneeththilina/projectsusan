from datetime import datetime, timezone

def unix_millis_to_utc(unix_millis):
    # Convert the Unix timestamp in milliseconds to seconds
    unix_seconds = unix_millis / 1000
    # Convert the Unix timestamp to a datetime object in UTC
    utc_datetime = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
    return utc_datetime

# Example usage
unix_millis = 1717090569743  # Example Unix timestamp in milliseconds
utc_datetime = unix_millis_to_utc(unix_millis)
print(utc_datetime)  # Output: 2024-05-31 02:56:09.743000+00:00

# Formatting the output
formatted_utc = utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f %Z')
print(formatted_utc)  # Output: 2024-05-31 02:56:09.743000 UTC
