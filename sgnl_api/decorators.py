def extract_key_from_response(key: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)
            if isinstance(response, dict) and key in response:
                return response[key]
            return response
        return wrapper
    return decorator
