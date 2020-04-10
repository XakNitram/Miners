from dataclasses import dataclass
from typing import List, Union, Tuple

import numpy as np
import pyglet
from math import cos, sin


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

    def transform_no_rotate(
            self, dx: float, dy: float,
            sx: float, sy: float
    ) -> np.ndarray:
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
