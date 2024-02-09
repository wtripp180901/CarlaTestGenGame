import fnmatch
import math

class Client:
    def __init__(self,dummyAddress,dummyPortNo):
        self.world = World()
    
    def get_world(self):
        return self.world

class Actor:
    def __init__(self,type_id,location):
        self.type_id = type_id
        self.attributes = {"role_name": None}
        self.bounding_box = Vector3D(0.5,0.5,1)
        self.location = location
        self.velocity = Vector3D(0,0,0)
    
    def get_velocity(self):
        return self.velocity
    def get_location(self):
        return self.location
        
class ActorList:
    def __init__(self,actors):
        self.actors = actors
    def filter(self,pattern):
        return [n for n in self.actors if fnmatch.fnmatch(n.type_id,pattern)]

class BoundingBox:
    def __init__(self,extent):
        self.extent = extent

class World:
    def __init__(self):
        self.actors = []
    def get_actors(self):
        return ActorList(self.actors)

class Location:
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z

class Vector3D:
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z
    def __add__(self,other):
        return Vector3D(self.x + other.x,self.y + other.y,self.z + other.z)
    def __sub__(self,other):
        return Vector3D(self.x - other.x,self.y - other.y,self.z - other.z)
    def __mul__(self,other):
        return Vector3D(self.x * other.x,self.y * other.y,self.z * other.z)
    def __truediv__(self,other):
        return Vector3D(self.x / other.x,self.y / other.y,self.z / other.z)
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    def cross(self,vector):
        return Vector3D(self.y * vector.z - self.z * vector.y,
                         self.z * vector.x - self.x * vector.z,
                         self.x * vector.y - self.y * vector.x)
