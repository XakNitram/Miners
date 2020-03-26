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
from typing import List, Tuple, Optional, Union

import numpy as np
import pyglet

from pyglet.graphics.vertexdomain import VertexList

from intersections import Rectangle


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

    def transform_no_rotate(self, dx: float, dy: float, sx: float, sy: float):
        return self.mesh @ np.array([
            [sx, 0., 0., 0.],
            [0., sy, 0., 0.],
            [0., 0., 1., 0.],
            [dx, dy, 0., 1.]
        ], dtype=float)

    def add_to_batch(
            self, batch: pyglet.graphics.Batch,
            group: pyglet.graphics.Group = None,
            *data: Union[str, Tuple[str, Union[Tuple[float, ...], List[float]]]]
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

    def __init__(self):
        self.vbo: Optional[VertexList] = None
        self.broken = False

    def update(self, x: float, y: float):
        self.vbo.vertices = self.shape.transform_no_rotate(
            x, y, self.size, self.size
        ).flatten()


class Chunk:
    __slots__ = ["data", "name", "offset", "disabled"]

    def __init__(self, name: int, offset: Tuple[float, float]):
        self.data: List[Block] = [Block() for i in range(256)]
        self.name = name
        self.offset = offset
        self.disabled = True

    def disable(self):
        if not self.disabled:
            for i in range(256):
                self.data[i].vbo.delete()
                self.data[i].vbo = None

            self.disabled = True

    def enable(self, batch):
        if self.disabled:
            ox, oy = self.offset
            for i in range(16):
                for j in range(16):
                    block = self.data[i * 16 + j]
                    block.vbo = block.shape.add_to_batch(
                        batch, None, 'v4f/stream',
                        ('c3f/static', [1., 0., 0.] * 4)
                    )
                    block.update(
                        float((i & 0xFF) * block.size + ox),
                        float((j & 0xFF) * block.size + oy)
                    )

            self.disabled = False

    @property
    def rectangle(self) -> Rectangle:
        ox, oy = self.offset
        scale = 16 * Block.size
        return Rectangle(ox, oy, scale, scale)


class Board:
    """Collection of chunks."""
    def __init__(self, batch, camera, width, height):
        self.batch = batch
        self.camera = camera

        # We only need to load 9 chunks at any time,
        # but we'd need to find some way to cache
        # the already loaded chunks that are out of view.
        self.chunks = [
            Chunk(0, (width / 2 - 256, height / 2 - 256))
        ]

        for chunk in self.chunks:
            chunk.enable(batch)

    def update(self, dt):
        # the scale added will depend on the camera's movement speed.
        camera_rect = self.camera.rectangle.scale(200., 200.)
        for chunk in self.chunks:
            if not chunk.disabled:
                if not camera_rect.intersects(chunk.rectangle):
                    chunk.disable()
            else:
                if camera_rect.intersects(chunk.rectangle):
                    chunk.enable(self.batch)


class Camera:
    __slots__ = ['x', 'y', "width", "height"]

    near = -1.
    far = 1.

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def project(self, dx, dy):
        self.x -= 10. * dx
        self.y -= 10. * dy

        pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
        pyglet.gl.glLoadIdentity()
        pyglet.gl.glOrtho(
            self.x, self.x + self.width,
            self.y, self.y + self.height,
            self.near, self.far
        )

        pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)

    @property
    def rectangle(self) -> Rectangle:
        return Rectangle(self.x, self.y, self.width, self.height)


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

        self.chunk = Chunk(0, (width / 2 - 256, height / 2 - 256))
        self.chunk.enable(self.batch)

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
