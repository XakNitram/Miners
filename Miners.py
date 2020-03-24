"""
A slight change to MinerTest, we want this version to have an infinite world
the viewer can pan around.

We'll make the chunk size 16x16.
To start, we will not have depth.

We will start by just drawing quads.

How do we handle an infinite world with batch rendering?
I think we do a check over all loaded blocks to see
if they fall within the viewport. If not, we do VertexList.delete,
else, we add to the batch.
"""
from dataclasses import dataclass
from math import cos, sin
from typing import List, Tuple

import numpy as np
import pyglet


@dataclass
class Shape:
    mesh: np.ndarray
    mode: int
    indices: List[int]

    def transform(
            self, dx: float, dy: float, angle:
            float, sx: float, sy: float
    ) -> np.ndarray:
        return self.mesh @ np.array([
            [sx * cos(angle),  sx * sin(angle), 0., 0.],
            [sy * -sin(angle), sy * cos(angle), 0., 0.],
            [0.,               0.,              1., 0.],
            [dx,               dy,              0., 1.]
        ], dtype=float)

    def add_to_batch(
            self, batch: pyglet.graphics.Batch,
            group: pyglet.graphics.Group = None,
            *data: str
    ) -> pyglet.graphics.vertexdomain.VertexList:
        return batch.add_indexed(
            4, self.mode, group,
            self.indices, *data
        )


quad = Shape(
    np.array([
        [0., 0., 0., 1.],
        [1., 0., 0., 1.],
        [1., 1., 0., 1.],
        [0., 1., 0., 1.]
    ], dtype=float),
    pyglet.gl.GL_TRIANGLES,
    [0, 1, 2, 2, 3, 0]
)


line_quad = Shape(
    np.array([
        [0., 0., 0., 1.],
        [1., 0., 0., 1.],
        [1., 1., 0., 1.],
        [0., 1., 0., 1.]
    ], dtype=float),
    pyglet.gl.GL_LINES,
    [0, 1, 1, 2, 2, 3, 3, 0]
)


class Block:
    __slots__ = ["broken", "vbo"]
    shape = line_quad
    size = 32

    def __init__(self, vbo: pyglet.graphics.vertexdomain.VertexList):
        self.broken = False
        self.vbo = vbo

    def update(self, x: float, y: float):
        self.vbo.vertices = self.shape.transform(
            x, y, 0., self.size, self.size
        ).flatten()


class Chunk:
    def __init__(self, offset: Tuple[float, float]):
        self.data: List[Block] = [None] * (16 * 16)
        self.offset = offset

    def fill(self, batch: pyglet.graphics.Batch):
        ox, oy = self.offset
        for i in range(16):
            for j in range(16):
                block = Block(
                    batch.add_indexed(
                        4, Block.shape.mode, None, Block.shape.indices,
                        'v4f/stream', ('c3f/static', [1., 0., 0.] * 4)
                    )
                )

                self.data[i * 16 + j] = block
                block.update(
                    float((i & 0xFF) * block.size + ox),
                    float((j & 0xFF) * block.size + oy)
                )


class Board:
    """Collection of chunks."""
    pass


class Camera:
    __slots__ = ['x', 'y', "width", "height"]

    near = -50
    far = 50

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def project(self, dx, dy):
        # pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
        # pyglet.gl.glLoadIdentity()
        # pyglet.gl.glViewport(self.x, self.y, self.width, self.height)
        # pyglet.gl.glOrtho(0, self.width, 0, self.height, self.near, self.far)
        # pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)

        self.x += 10. * dx
        self.y += 10. * dy
        pyglet.gl.glTranslatef(10. * dx, 10. * dy, 0.)


class Simulation:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.window = pyglet.window.Window(
            width=self.width, height=self.height,
            vsync=True,
        )

        self.keys = pyglet.window.key.KeyStateHandler()
        self.window.push_handlers(self.keys)
        self.window.push_handlers(self.on_draw)

        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(0., 0., width, height)

        self.chunk = Chunk((width / 2 - 256, height / 2 - 256))
        self.chunk.fill(self.batch)

    def update(self, dt: float):
        dx = self.keys[pyglet.window.key.A] - self.keys[pyglet.window.key.D]
        dy = self.keys[pyglet.window.key.S] - self.keys[pyglet.window.key.W]
        self.camera.project(dx, dy)

    def on_draw(self):
        self.window.clear()
        self.batch.draw()

        pyglet.graphics.draw(
            4, pyglet.gl.GL_QUADS,
            ('v2f/static', [
                self.width - 75, self.height - 75,
                self.width - 25, self.height - 75,
                self.width - 25, self.height - 25,
                self.width - 75, self.height - 25
            ])
        )

    def setup(self):
        pyglet.clock.schedule_interval(
            self.update, 1. / 60.
        )

    def run(self):
        self.setup()
        pyglet.app.run()


if __name__ == '__main__':
    sim = Simulation(800, 640)
    sim.run()
