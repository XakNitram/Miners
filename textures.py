from typing import NamedTuple, Tuple, Optional, Dict

import pyglet
from pyglet.image import Texture


class Descriptor(NamedTuple):
    coordinates: Tuple[int, int, int, int]


class Atlas:
    """Texture map class to store images efficiently under key names."""

    __slots__ = ['_image', 'image_descriptors']

    from json import load as load_json

    def __init__(self):
        self._image: Optional[Texture] = None
        self.image_descriptors: Dict[str, Descriptor] = {}

    @property
    def image(self) -> Texture:
        if self._image is None:
            raise ValueError('atlas was not first initialized with the load method')
        return self._image

    @image.setter
    def image(self, value: Texture):
        self._image = value

    def load(self, image_file: str, atlas_file: str):
        """
        :param str image_file:  Atlas image file (see minecraft texture atlas)
        :param str atlas_file:  Atlas description file

        Recognized atlas description format (json):
        {
            "STONE_COLUMN": {
                "coordinates": [
                    0,   // x
                    0,   // y
                    16,  // width
                    16   // height
                ]
            },
            "STONE_FLOOR": {
                "coordinates": [
                    0,
                    16,
                    16,
                    16
                ]
            }
        }

        :return:
        """
        self._image = pyglet.resource.texture(image_file)

        with open(atlas_file, 'r') as descriptor_file:
            file = self.load_json(descriptor_file)

        for name, texture in file.items():
            coordinates = texture['coordintates']
            descriptor = Descriptor(coordinates)

            self.image_descriptors[name] = descriptor

    def __getitem__(self, item: str):
        try:
            descriptor = self.image_descriptors[item]
        except KeyError:
            raise
        return self.image.get_region(
            *descriptor.coordinates
        )
