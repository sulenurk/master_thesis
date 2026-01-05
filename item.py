#item.py
class Item:
    def __init__(self, item_id, length, width, order_id=None):
        """
        Initialize an Item with given dimensions
        
        Args:
            item_id: Unique identifier for the item
            length: Length of the item
            width: Width of the item
        """
        self.item_id = item_id
        self.order_id = order_id
        self.length = length
        self.width = width
        self.x = None  # Position on pallet (None means not placed)
        self.y = None
        self.rotated = False  # Rotation status
    
    def rotate(self):
        """
        Rotate the item 90 degrees (swap length and width)
        Returns the item itself for method chaining
        """
        self.length, self.width = self.width, self.length
        self.rotated = not self.rotated
        return self
    
    @property
    def area(self):
        """Calculate and return the area of the item"""
        return self.length * self.width
    
    def get_bounding_box(self):
        """
        Get the bounding box coordinates of the item if placed
        Returns (x1, y1, x2, y2) or None if not placed
        """
        if self.x is None or self.y is None:
            return None
        return (self.x, self.y, self.x + self.length, self.y + self.width)
    
    def __repr__(self):
        """String representation of the item"""
        status = f"at ({self.x},{self.y})" if self.x is not None else "unplaced"
        rotation = "rotated" if self.rotated else "original"
        return f"Item(id={self.item_id}, {self.length}x{self.width}, {rotation}, {status})"
    
    def copy(self):
        """Create a copy of this item"""
        new_item = Item(self.item_id, self.length, self.width, self.order_id)
        new_item.x = self.x
        new_item.y = self.y
        new_item.rotated = self.rotated
        return new_item