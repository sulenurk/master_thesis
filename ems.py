#ems.py
class EMS:
    """Empty Maximal Space"""
    def __init__(self, x, y, length, width):
        self.x = x
        self.y = y
        self.length = length
        self.width = width
        self.area = length * width
    
    def __repr__(self):
        return f"EMS({self.x},{self.y},{self.length}x{self.width})"