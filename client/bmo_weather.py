import httpx
from tools import tool
import os
from dotenv import load_dotenv


class BMOWeather:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall?"
        self.geo_decoding_url = "http://api.openweathermap.org/geo/1.0/direct?"

    @tool
    def weather_data(self, location: str):
        """Get the current weather for a location.

        Args:
            location: The city name to get weather for, e.g. 'Toronto'
        """
        with httpx.Client() as client:
            try:
                geo = client.get(f"{self.geo_decoding_url}q={location}&limit=1&appid={self.api_key}")
                geo_data = geo.json()[0]
                response = client.get(
                    f"{self.base_url}lat={geo_data['lat']}&lon={geo_data['lon']}"
                    f"&exclude=minutely,hourly,daily,alerts&appid={self.api_key}"
                )
                return response.json()
            except Exception as e:
                return f"Failed to get weather for {location}: {e}"

weather = BMOWeather()
