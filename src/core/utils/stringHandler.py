import random
import string
from .timezoneHandler import TimezoneHandler


class StringHandler:
    @staticmethod
    def generate_random_string(length=16):
        """
        Generates a Random String of the Given Length

        Args:
            length (int, optional): The length of the random string to generate. Defaults to 16.
        """
        characters = string.ascii_letters + string.digits
        random_string = "".join(random.choice(characters) for _ in range(length))
        date_str = TimezoneHandler.now("UTC").strftime("%Y%m%d%H%M%S")
        minimum_diff = 6
        if length - len(date_str) > minimum_diff - 1:
            random_string = random_string[: -len(date_str)] + date_str
        return random_string

    @staticmethod
    def generate_random_number(length=6):
        """
        Generates a Random Number of the Given Length

        Args:
            length (int, optional): The length of the random number to generate. Defaults to 6.
        """
        if length < 1:
            raise ValueError("Length must be a positive integer.")
        digits = string.digits
        random_number = "".join(random.choice(digits) for _ in range(length))
        return random_number
