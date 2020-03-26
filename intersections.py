from dataclasses import dataclass

from pyglet.graphics import draw_indexed
from pyglet.gl import GL_LINES


@dataclass
class Rectangle:
    x: float
    y: float
    w: float
    h: float

    def intersects(self, other: "Rectangle"):
        return not (
            other.x > self.x + self.w
            or other.x + other.w < self.x
            or other.y > self.y + self.h
            or other.y + other.h < self.y
        )

    def scale(self, sx: float, sy: float):
        """
        zyyyz ) where:
        xooox )   o = Rectangle(..., ..., o, o) (original)
        xooox )   x = Rectangle(..., ..., x, 0) (scale x)
        xooox )   y = Rectangle(..., ..., 0, y) (scale y)
        zyyyz )   z = Rectangle(..., ..., x, y) (corners)
        """
        return Rectangle(
            self.x - sx,     self.y - sy,
            self.w + sx * 2, self.h + sy * 2
        )

    def draw(self):
        draw_indexed(4, GL_LINES, [0, 1, 1, 2, 2, 3, 3, 0], ('v2f', [
            self.x, self.y,
            self.x + self.w, self.y,
            self.x + self.w, self.y + self.h,
            self.x, self.y + self.h
        ]))
