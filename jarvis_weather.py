import httpx
from anthropic import beta_tool
import os
from dotenv import load_dotenv


class JarvisWeather:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall?"
        self.geo_decoding_url = "http://api.openweathermap.org/geo/1.0/direct?"

    def weather_request(self, location):
       with httpx.Client() as client:
           geo = client.get(f"{self.geo_decoding_url}q={location}&limit=1&appid={self.api_key}")
           print(geo.json())
           geo_data = geo.json()[0]
           print(geo_data)
           response = client.get(f"{self.base_url}lat={geo_data["lat"]}&lon={geo_data["lon"]}&exclude=minutely,hourly,daily,alerts&appid={self.api_key}")
           weather_data = response.json()
           return weather_data

weather = JarvisWeather()

@beta_tool
def weather_data(location):
    """
    Returns weather data for given location
    Args:
        location: The location to get weather data for

    Returns:
        A dictionary with weather data for given location
    """
    try:
        weather_data = weather.weather_request(location)
        return weather_data
    except Exception as e:
        return f"Failed to get weather data for {location} due to {e}"
