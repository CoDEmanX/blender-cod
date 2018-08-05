# <pep8 compliant>

import json
import zipfile
import struct

'''
    ---------------------------
    ---< SIEGE_ANIM_SOURCE >---
    ---------------------------
'''

# buffer() is required for file.writestr in Python 2.x but
#  is no longer required (and doesn't exist) in Python 3.x
try:
    buffer
except NameError:
    def buffer(data):
        return data


class Frame(object):
    __slots__ = ('index', 'position', 'rotation')

    def __init__(self, index=0, position=(0, 0, 0), rotation=(0, 0, 0, 1)):
        self.index = index
        self.position = position
        self.rotation = rotation


class Node(object):
    __slots__ = ('name', 'frames')

    def __init__(self, name=None, frames=0):
        self.name = name
        self.frames = [None] * int(frames)


class Shot(object):
    __slots__ = ('name', 'start', 'end')

    def __init__(self, name=None, start=0, end=360):
        self.name = name
        self.start = start
        self.end = end


class Info(object):
    __slots__ = ('argJson', 'computer', 'domain',
                 'ta_game_path', 'time', 'user')

    def __init__(self, argJson="{}", computer="D3V-137", domain="ATVI",
                 ta_game_path="c:\\", time="", user="d3v"):
        self.argJson = argJson
        self.computer = computer
        self.domain = domain
        self.ta_game_path = ta_game_path
        self.time = time
        self.user = user


class SiegeAnim(object):
    __slots__ = ('frames', 'nodes', 'shots',
                 'playback_speed', 'speed', 'loop', 'info')

    def __init__(self, frames=0, nodes=0, shots=0):
        self.frames = int(frames)
        self.nodes = [None] * int(nodes)
        self.shots = [None] * int(shots)
        self.playback_speed = 1
        self.speed = 0
        self.loop = True
        self.info = Info()

    def __load_positions__(self, data):
        # Load raw positions from the data buffer (3 floats 4 bytes each)
        buffer_offset = 0
        for frame in range(int(self.frames)):
            for node in self.nodes:
                trans = struct.unpack_from("fff", data, offset=buffer_offset)
                node.frames[frame] = Frame(frame, trans)
                buffer_offset = buffer_offset + 12

    def __load_rotations__(self, data):
        # Load raw rotations from the data buffer(4 floats, 4 bytes each)
        buffer_offset = 0
        for frame in range(int(self.frames)):
            for node in self.nodes:
                rot = struct.unpack_from("ffff", data, offset=buffer_offset)
                node.frames[frame].rotation = rot
                buffer_offset = buffer_offset + 16

    def __load_index__(self, file):
        # Load the serialized index file
        idx_parse = json.loads(file.read("index.json"))

        # All of this data is required so we must be able to load it
        self.frames = int(idx_parse["animation"]["frames"])
        self.loop = bool(idx_parse["animation"]["loop"])
        self.nodes = [None] * int(idx_parse["animation"]["nodes"])
        self.speed = int(idx_parse["animation"]["speed"])
        self.playback_speed = int(idx_parse["animation"]["playbackSpeed"])

        if idx_parse["info"] is not None:
            if idx_parse["info"]["argJson"] is not None:
                self.info.argJson = idx_parse["info"]["argJson"]
            if idx_parse["info"]["computer"] is not None:
                self.info.computer = idx_parse["info"]["computer"]
            if idx_parse["info"]["domain"] is not None:
                self.info.domain = idx_parse["info"]["domain"]
            if idx_parse["info"]["ta_game_path"] is not None:
                self.info.ta_game_path = idx_parse["info"]["ta_game_path"]
            if idx_parse["info"]["time"] is not None:
                self.info.time = idx_parse["info"]["time"]
            if idx_parse["info"]["user"] is not None:
                self.info.user = idx_parse["info"]["user"]

        if idx_parse["nodes"] is not None:
            for node_index, node in enumerate(idx_parse["nodes"]):
                self.nodes[node_index] = Node(node["name"], self.frames)

        if idx_parse["shots"] is not None:
            self.shots = [None] * len(idx_parse["shots"])
            for shot_index, shot in enumerate(idx_parse["shots"]):
                self.shots[shot_index] = Shot(
                    shot["name"], int(shot["start"]), int(shot["end"]))

        if idx_parse["data"] is not None:
            if idx_parse["data"]["data/positions"] is not None:
                # Load positions per node, per frame
                positions = file.read("data/positions")
                self.__load_positions__(positions)
            if idx_parse["data"]["data/quaternions"] is not None:
                # Load rotations per node, per frame
                rotations = file.read("data/quaternions")
                self.__load_rotations__(rotations)

    def __write_positions__(self, file):
        # Serialize the positions per node, per frame
        byte_stride = 12 * len(self.nodes)
        data_length = self.frames * len(self.nodes) * 12
        data_buffer = bytearray(int(data_length))
        data_offset = 0

        for frame in range(int(self.frames)):
            for node in self.nodes:
                struct.pack_into("fff", data_buffer, data_offset,
                                 *node.frames[frame].position)
                data_offset = data_offset + 12

        # Inject the data/positions file
        file.writestr("data/positions", buffer(data_buffer),
                      compress_type=zipfile.ZIP_DEFLATED)

        # Return buffer size and stride
        return (data_length, byte_stride)

    def __write_rotations__(self, file):
        # Serialize the positions per node, per frame
        byte_stride = 16 * len(self.nodes)
        data_length = self.frames * len(self.nodes) * 16
        data_buffer = bytearray(int(data_length))
        data_offset = 0

        for frame in range(int(self.frames)):
            for node in self.nodes:
                struct.pack_into("ffff", data_buffer, data_offset,
                                 *node.frames[frame].rotation)
                data_offset = data_offset + 16

        # Inject the data/quaternions file
        file.writestr("data/quaternions", buffer(data_buffer),
                      compress_type=zipfile.ZIP_DEFLATED)

        # Return buffer size and stride
        return (data_length, byte_stride)

    def __write_index__(self, file):
        # Serialize the data back to the file
        idx_dict = {}

        idx_dict["animation"] = {
            "frames": str(int(self.frames)),
            "loop": str(int(self.loop)),
            "nodes": str(len(self.nodes)),
            "playbackSpeed": str(self.playback_speed),
            "speed": str(self.speed)
        }

        idx_dict["info"] = {
            "argJson": self.info.argJson,
            "computer": self.info.computer,
            "domain": self.info.domain,
            "ta_game_path": self.info.ta_game_path,
            "time": self.info.time,
            "user": self.info.user
        }

        idx_dict["nodes"] = [None] * len(self.nodes)
        for node_index, node in enumerate(self.nodes):
            idx_dict["nodes"][node_index] = {"name": node.name}

        idx_dict["shots"] = [None] * len(self.shots)
        for shot_index, shot in enumerate(self.shots):
            idx_dict["shots"][shot_index] = {
                "name": shot.name,
                "end": str(shot.end), "start": str(shot.start)}

        # Inject the position and rotations data
        pos_data = self.__write_positions__(file)
        rot_data = self.__write_rotations__(file)

        # Apply the data block
        idx_dict["data"] = {
            "data/positions": {
                "byteSize": str(pos_data[0]),
                "byteStride": str(pos_data[1])
            },
            "data/quaternions": {
                "byteSize": str(rot_data[0]),
                "byteStride": str(rot_data[1])
            }
        }

        # Inject the index file
        file.writestr("index.json", json.dumps(idx_dict),
                      compress_type=zipfile.ZIP_DEFLATED)

    def LoadFile(self, path):
        file = zipfile.ZipFile(path, "r")
        self.__load_index__(file)
        file.close()

    def WriteFile(self, path):
        file = zipfile.ZipFile(path, "w")
        self.__write_index__(file)
        file.close()
