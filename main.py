import requests
from datetime import datetime, time as dt_time, timezone
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Your position
MY_LAT = -8.6399
MY_LONG = 61.3399
TOLERANCE = 5

# Email details
EMAIL = ""
PASSWORD = ""
RECIPIENT_EMAIL = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
TIMEOUT = 10  # Timeout for API requests in seconds


def get_iss_position():
    try:
        response = requests.get(url="http://api.open-notify.org/iss-now.json", timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        iss_latitude = float(data["iss_position"]["latitude"])
        iss_longitude = float(data["iss_position"]["longitude"])
        return iss_latitude, iss_longitude
    except requests.RequestException as e:
        print(f"Error fetching ISS position: {e}")
        return None, None


def get_sunrise_sunset():
    parameters = {
        "lat": MY_LAT,
        "lng": MY_LONG,
        "formatted": 0,
    }
    try:
        response = requests.get("https://api.sunrise-sunset.org/json", params=parameters, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        sunrise = data["results"]["sunrise"].split("T")[1].split(":")[0:2]
        sunset = data["results"]["sunset"].split("T")[1].split(":")[0:2]

        sunrise_hour = int(sunrise[0])
        sunrise_minute = int(sunrise[1])
        sunset_hour = int(sunset[0])
        sunset_minute = int(sunset[1])

        return dt_time(sunrise_hour, sunrise_minute), dt_time(sunset_hour, sunset_minute)
    except requests.RequestException as e:
        print(f"Error fetching sunrise and sunset times: {e}")
        return None, None


def is_within_range(my_lat, my_long, iss_lat, iss_long, tolerance):
    lat_range = (iss_lat - tolerance) <= my_lat <= (iss_lat + tolerance)
    long_range = (iss_long - tolerance) <= my_long <= (iss_long + tolerance)
    return lat_range and long_range


def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    for attempt in range(3):  # Retry up to 3 times
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as connection:  # Use SMTP_SSL for port 465
                connection.login(EMAIL, PASSWORD)
                connection.send_message(msg)
                print("Email sent successfully")
                break
        except smtplib.SMTPServerDisconnected as e:
            print(f"SMTPServerDisconnected error on attempt {attempt + 1}: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying
        except smtplib.SMTPException as e:
            print(f"SMTPException on attempt {attempt + 1}: {e}")
            break


while True:
    iss_latitude, iss_longitude = get_iss_position()
    sunrise, sunset = get_sunrise_sunset()
    if iss_latitude is None or iss_longitude is None or sunrise is None or sunset is None:
        print("Skipping this check due to an error in fetching data.")
        time.sleep(60)
        continue

    current_time = datetime.now(timezone.utc).time()

    if is_within_range(MY_LAT, MY_LONG, iss_latitude, iss_longitude, TOLERANCE):
        if current_time < sunrise or current_time > sunset:
            print("ISS position is close to your current location, look up")
            send_email(
                subject="Look Up!",
                body="The ISS is above you in the sky."
            )
        else:
            print("It's daytime, the ISS might not be visible")
            send_email(
                subject="Daytime Alert",
                body="The ISS is above you, but it's daytime, so it might not be visible."
            )
    else:
        print("ISS position is not close to your current location")

    print(f"Your Position: {MY_LAT}, {MY_LONG}")
    print(f"ISS Position: {iss_latitude}, {iss_longitude}")

    # Wait for 60 seconds before checking again
    time.sleep(60)
