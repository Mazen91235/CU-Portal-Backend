from utils import validate_id
def is_national_id(national_id: str) -> bool:
    """
    Validates if the provided string is a valid Egyptian national ID.
    The ID should be 14 digits long and follow specific rules:
    - User must be born between 1980 and 2010 (so the first digit is 2 or 3)
    - User must be born in Egypt
    """
    try:
        result = validate_id(national_id)
        print(result)
        if not result:
            return False
        year = int(result.get("Year"))
        if year < 1980 or year > 2010:
            return False
        return True
    except Exception:
        return False

print(is_national_id("30512198800037"))  # Valid ID