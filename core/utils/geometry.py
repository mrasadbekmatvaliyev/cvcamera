def is_crossing_line(prev_y, curr_y, line_y):
    """
    Checks if an object has crossed a horizontal line between two frames.
    
    Args:
        prev_y: Y-coordinate in the previous frame.
        curr_y: Y-coordinate in the current frame.
        line_y: Y-coordinate of the detection line.
        
    Returns:
        bool: True if crossing occurred, False otherwise.
    """
    if prev_y is None:
        return False
    # Case 1: Moving Down (prev_y <= line_y and curr_y > line_y)
    # Case 2: Moving Up (prev_y >= line_y and curr_y < line_y)
    return (prev_y <= line_y < curr_y) or (curr_y <= line_y < prev_y)
