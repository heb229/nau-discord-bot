# imports
    # none

# function to format name for display
def format_full_name(roster_name: str) -> str:
    """
    Converts 'Lastname, Firstname MiddleNames' 
    to 'Firstname MiddleNames Lastname'
    """

    # checks for valid formatting
    if "," not in roster_name:
        # raises error if invalid
        raise ValueError("Invalid name format")
    
    # if valid, pulls the name and reformats 
    last, first = roster_name.split(",", 1)

    # returns the reformatted name: first, middle, last
    return f"{first.strip()} {last.strip()}"
