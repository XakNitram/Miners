from dataclasses import dataclass


@dataclass
class Rectangle:
    x: float
    y: float
    w: float
    h: float

    def intersects(self, rect: "Rectangle"):
        return not (
            rect.x > self.x + self.w
            or rect.x + rect.w < self.x
            or rect.y > self.y + self.h
            or rect.y + rect.h < self.y
        )
