"""
    Conversions to be re-used whereever needed
"""

def get_int_value(value: str, max_value: int = 2**32 - 1):
    """
    Parses a string containing numbers in different formats and returns
    the corresponding integer value.
    
    Supported formats:
    - Decimal: '123'
    - Hexadecimal: '0xABC' or '0XaBc'
    - Binary: '0b101' or '0B101'
    
    Args:
        value (str): The string to be parsed
        max_value (int): a maximum value for additional plausibility check
        
    Returns:
        int: The parsed integer value
        None: If the string cannot be parsed as a number or out of valid range
    """
    # Remove whitespace at the beginning and end, make lowercase
    value = value.strip().lower()
    try:
        # Check the format and apply the appropriate conversion
        if value.startswith('0x'):
            # Hexadecimal format
            value_int = int(value, 16)
        elif value.startswith('0b'):
            # Binary format
            value_int = int(value, 2)
        else:
            # Treat as decimal number
            value_int = int(value)
        
        # Check whether value is in valid range
        if 0 <= value_int <= max_value:
            return value_int
    except:
        pass
    
    # parsing errors occured, return None
    return None
