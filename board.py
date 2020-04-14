from collections import deque
from dataclasses import dataclass
from math import atan2, tau
from random import random, shuffle, randrange
from typing import Optional, Tuple, List, Deque, Set, Union

from pyglet import gl
from pyglet.graphics import Group, OrderedGroup, Batch
from pyglet.graphics.vertexdomain import VertexList
from pyglet.image import Texture
from pyglet.resource import texture
from pyglet.sprite import Sprite

from camera import Camera
from common import global_timer, GRID_SIZE
from intersections import Rectangle
from shapes import quad, line_quad


class TextureGroup(Group):

    def __init__(
            self, tex: Texture,
            parent: Group = None
    ):
        super().__init__(parent)
        self.texture = tex
        self.blend_src = gl.GL_SRC_ALPHA
        self.blend_dest = gl.GL_ONE_MINUS_SRC_ALPHA

    def set_state(self):
        gl.glEnable(self.texture.target)
        gl.glBindTexture(self.texture.target, self.texture.id)

        gl.glTexParameteri(
            gl.GL_TEXTURE_2D,
            gl.GL_TEXTURE_MAG_FILTER,
            gl.GL_NEAREST
        )

        gl.glPushAttrib(gl.GL_COLOR_BUFFER_BIT)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(self.blend_src, self.blend_dest)

    def unset_state(self):
        gl.glPopAttrib()
        gl.glDisable(self.texture.target)


@dataclass
class Position:
    x: float = 0.
    y: float = 0.


@dataclass
class Index:
    i: int = 0
    j: int = 0


@dataclass
class Block:
    # position: Position = Position(0., 0.)  # why did we want this?
    broken: bool = False
    value: int = 0


# TEXTURES = [
#         texture("Data/Environment/FLOOR_01.png"),
#         texture("Data/Environment/FLOOR_02.png"),
#         texture("Data/Environment/FLOOR_03.png")
#     ]
#
# MINER_TEXTURE = texture("Data/Environment/pickaxe.png")
# MINER_TEXTURE.width *= 2
# MINER_TEXTURE.height *= 2
#
BLOCKS = OrderedGroup(0)
MINERS = OrderedGroup(1)
BORDER = OrderedGroup(2)
# GROUPS = [TextureGroup(TEXTURES[i], BLOCKS) for i in range(3)]


class Miner:
    SPEED = 1.

    def __init__(self, x, y, batch: Batch):
        self.position = Position(x, y)
        self.index = Index()

        # self.sprite = Sprite(
        #     MINER_TEXTURE, self.position.x, self.position.y,
        #     batch=batch, group=MINERS, subpixel=True
        # )

        self.vbo = batch.add_indexed(
            4, quad.mode, MINERS, quad.indices,
            ('v4f', quad.transform_no_rotate(x, y, GRID_SIZE, GRID_SIZE).flatten())
        )

        self.move_time = 0.

    def teleport(self):
        size = GRID_SIZE

        i = randrange(1, -2, -1)
        j = randrange(1, -2, -1)
        self.index.i += i
        self.index.j += j
        x = self.position.x + i * size
        y = self.position.y + j * size

        # self.sprite.update(x, y)
        self.vbo.vertices = quad.transform_no_rotate(x, y, size, size).flatten()
        self.position.x = x
        self.position.y = y

    def update(self, dt: float):
        self.move_time += dt

        if self.move_time >= self.SPEED:
            self.move_time = 0.
            self.teleport()


class Chunk:
    # BLOCK_SHAPE = quad
    BLOCK_SHAPE = line_quad

    def __init__(self, name: int, offset: Tuple[float, float]):
        self.blocks: List[Block] = [Block(value=randrange(3)) for _ in range(256)]
        self.vbos: List[Optional[VertexList]] = [None for _ in range(256)]
        self.name = name
        self.offset = offset
        self.visible = False

        self.bound = None

        self.show_queue: Deque[Tuple[int, int]] = deque(maxlen=16)

    def __repr__(self):
        x, y = self.offset
        return f"Chunk({self.name:d}, ({x:f}, {y:f}))"

    def hide(self):
        """Disable the chunk. Will be later converted to asynchronous code."""
        # print(f"disabling the chunk {self.name}")

        if not self.visible:
            for i in range(256):
                vbo = self.vbos[i]
                if vbo is not None:
                    self.vbos[i].delete()
                    self.vbos[i] = None

            self.show_queue.clear()

            if self.bound is not None:
                self.bound.delete()
                self.bound = None

    def show(self, batch: Batch, view_box: Rectangle):
        """Start the chunk loading process."""
        # print(f"enabling the chunk {self.name}")

        if self.visible:
            ox, oy = self.offset
            self.show_queue.clear()

            # angle-based loading
            # vx, vy = view_box.center
            # sx, sy = self.rectangle.center
            #
            # # load in 4 x 4 squares
            # angle = atan2(vy - sy, vx - sx) % tau
            # t16 = tau / 16
            # if t16 * 15 < angle + tau < tau + t16:
            #     for i in range(4):
            #         for j in range(4):
            #             self.show_queue.append((i, j))
            # elif t16 < angle < tau * 3:
            #     for n in range(1, -1, -1):
            #         for m in range(1, -1, -1):
            #             for j in range(1, -1, -1):
            #                 for i in range(1, -1, -1):
            #                     self.show_queue.append((m * 2 + i, n * 2 + j))
            # elif t16 * 7 < angle < t16 * 9:
            #     for i in range(3, -1, -1):
            #         for j in range(4):
            #             self.show_queue.append((i, j))
            # elif t16 * 3 < angle < t16 * 5:
            #     for j in range(4):
            #         for i in range(3, -1, -1):
            #             self.show_queue.append((i, j))
            # elif t16 * 11 < angle < t16 * 13:
            #     for j in range(3, -1, -1):
            #         for i in range(4):
            #             self.show_queue.append((i, j))

            for j in range(4):
                for i in range(4):
                    self.show_queue.append((i, j))
            shuffle(self.show_queue)

            self.bound = line_quad.add_to_batch(
                batch, BORDER, (
                    'v4f', line_quad.transform_no_rotate(
                        ox, oy, 16 * GRID_SIZE, 16 * GRID_SIZE
                    ).flatten()
                )
            )

    def process(self, batch) -> bool:
        if not len(self.show_queue):
            return True

        scale = GRID_SIZE
        ox, oy = self.offset
        for _ in range(4):
            i, j = self.show_queue.pop()
            for n in range(4):
                for m in range(4):
                    index = (j * 64) + (i * 16) + (n * 4) + m
                    # value = self.blocks[index].value
                    group = BLOCKS
                    # group = GROUPS[value]
                    self.vbos[index] = self.BLOCK_SHAPE.add_to_batch(
                        batch, group, (
                            'v4f/static', self.BLOCK_SHAPE.transform_no_rotate(
                                (i * 4 + m) * scale + ox,
                                (j * 4 + n) * scale + oy,
                                scale, scale
                            ).flatten()),
                        ('c3B/static', [0x3e, 0x41, 0x4e] * 4)
                        # ("t3f", TEXTURES[value].tex_coords)
                    )

        return False

    @property
    def rectangle(self) -> Rectangle:
        ox, oy = self.offset
        scale = 16 * GRID_SIZE
        return Rectangle(ox, oy, scale, scale)


class ChunkGrid:
    """Construct to handle chunk loading and unloading."""

    def __init__(self, initial_width, initial_height):
        self.chunks: List[Chunk] = []

        w2 = initial_width / 2
        h2 = initial_height / 2
        cx = cy = 16 * GRID_SIZE
        xr = yr = 5

        # self.chunks = [
        #     Chunk(0, (offset_x0, offset_y0)),
        #     Chunk(1, (offset_x1, offset_y1)),
        #     Chunk(2, (offset_x2, offset_y2)),
        #         ...,
        #     CHunk(n, (w2 + cx * (n - xr / 2, h2 + cy * (n - xr / 2))
        # ]

        for j in range(yr):
            for i in range(xr):
                index = j * yr + i

                self.chunks.append(Chunk(index, (
                    w2 + cx * (i - xr / 2),
                    h2 + cy * (j - yr / 2)
                )))

        self.loading: List[Set[int]] = [
            set(),  # load vbos
            set(),  # delete vbos
            set(),  # load data
            set()   # save data
        ]

        self.current: int = -1

    def __getitem__(self, item: Union[int, slice]) -> Chunk:
        return self.chunks[item]

    def process_graphics(self, batch: Batch, view_box: Rectangle):
        visible, hidden, available, unavailable = self.loading

        for i, chunk in enumerate(self.chunks):
            if not chunk.visible and view_box.intersects(chunk.rectangle):
                visible.add(i)
                chunk.visible = True

                if i in hidden:
                    hidden.discard(i)
            elif chunk.visible and not view_box.intersects(chunk.rectangle):
                hidden.add(i)
                chunk.visible = False

                if i in visible:
                    visible.discard(i)

        showing = len(visible)
        hiding = len(hidden)

        if showing and (hiding == 0 or random() > 0.5) and self.current < 0:
            index = visible.pop()
            chunk = self[index]
            chunk.show(batch, view_box)

            self.current = index

        elif hiding and (showing == 0 or random() > 0.5):
            chunk = self[hidden.pop()]
            chunk.hide()

        if self.current > -1:
            chunk = self[self.current]
            if chunk.process(batch):
                self.current = -1


class Board:
    """Collection of chunks."""
    def __init__(
            self, batch: Batch, camera: Camera,
            init_width: int, init_height: int
    ):
        self.batch = batch
        self.camera = camera

        self.chunks: ChunkGrid = ChunkGrid(init_width, init_height)
        ox, oy = self.chunks[12].offset
        i, j = randrange(16), randrange(16)
        x = (i * GRID_SIZE) + ox
        y = (j * GRID_SIZE) + oy
        self.miners = []
        for i in range(10):
            self.miners.append(Miner(x, y, batch))

    @global_timer.timed
    def update(self, dt):
        # the scale added will depend on the camera's movement speed.
        # view_box = self.camera.rectangle.scale(-200., -200.)
        view_box = self.camera.rectangle

        for miner in self.miners:
            miner.update(dt)
        self.chunks.process_graphics(self.batch, view_box)
