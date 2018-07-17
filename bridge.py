#!/usr/bin/python3
import gevent
from gevent import monkey
monkey.patch_all()
import Pyrlang
from Pyrlang import Atom, Process
import rospy
from std_msgs.msg import String, Int16, Bool, Float32
from geometry_msgs.msg import Vector3
bp = None
global registeredPublishers
registeredListeners={}
registeredPublishers={}

def callback(msg, topic):
    print(dir(msg))
    global bp
    rospy.loginfo(rospy.get_caller_id() + "I heard %s", msg.data)
    bp.sendString(topic, msg.data)
def callback_vector3(msg, topic):
    global bp
    bp.sendString(topic, (msg.x, msg.y, msg.z))
    
def listener():
    # In ROS, nodes are uniquely named. If two nodes with the same
    # node are launched, the previous one is kicked off. The
    # anonymous=True flag means that rospy will choose a unique
    # name for our 'listener' node so that multiple listeners can
    # run simultaneously.
    rospy.init_node('listener', anonymous=True)
    rospy.Subscriber("chatter", String, callback, "chatter")
    rospy.spin()

class MyProcess(Process):
    def __init__(self, node) -> None:
        Process.__init__(self, node)
        self._node = node;
        self._node.register_name(self, Atom('pyBridge'))  # optional
        print("registering process - 'pyBridge'")

    def handle_one_inbox_message(self, msg):
        global registeredPublishers
        print("Incoming", msg)
        remotePid = msg[0]
        action = msg[1]
        if action == Atom('stop'):
            exit(0)
        msgType = msg[2]
        topic = msg[3]
        if action == Atom('subscribe'):
            if topic+"__"+str(msgType) in registeredListeners.keys():
                print("already listening to topic " + topic)
                self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('err'), Atom('already_subscribed'))))
            else:
                print("subscribing to " + topic)
                if msgType == Atom('string'):
                    sub=rospy.Subscriber(topic, String, callback, topic)
                elif msgType == Atom('int16'):
                    sub=rospy.Subscriber(topic, Int16, callback, topic)
                elif msgType == Atom('vector3'):
                    sub=rospy.Subscriber(topic, Vector3, callback_vector3, topic)
                else:
                    self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('err'), Atom('unknown_message_type'), msgType)))
                    return
                registeredListeners[topic+"__"+str(msgType)]=sub
                print(self.pid_)
                print(remotePid)
                self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('ok'), topic)))
        elif action == Atom('publish'):
            data=msg[4]
            if not topic in registeredPublishers.keys():
                if msgType == Atom('string'):
                    registeredPublishers[topic]=rospy.Publisher(topic, String, queue_size=0)
                    rospy.sleep(.1)
                if msgType == Atom('int16'):
                    registeredPublishers[topic]=rospy.Publisher(topic, Int16, queue_size=0)
                    rospy.sleep(.1)
                if msgType == Atom('float32'):
                    registeredPublishers[topic]=rospy.Publisher(topic, Float32, queue_size=0)
                    rospy.sleep(0.1)
                if msgType == Atom('bool'):
                    registeredPublishers[topic]=rospy.Publisher(topic, Bool, queue_size=0)
                    rospy.sleep(.1)
            if msgType == Atom('string'):
                registeredPublishers[topic].publish(String(data))
            elif msgType == Atom('int16'):
                registeredPublishers[topic].publish(Int16(data))
            elif msgType == Atom('float32'):
                registeredPublishers[topic].publish(Float32(data))
            elif msgType == Atom('bool'):
                registeredPublishers[topic].publish(Bool(data))
            else:
                self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('err'), Atom('unknown_message_type'), msgType)))
                return
            self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('ok'), topic)))
        else:
            self._node.send(sender=self.pid_, receiver=remotePid, message=(self.pid_, (Atom('err'), Atom('invalid_request'))))

    def sendString(self, topic, data):
        self._node.send(sender=self.pid_, receiver=(Atom('erl@x1'), Atom('erlBridge')), message=(self.pid_, (Atom('push'), topic, data)))
    def sendTest(self):
        self._node.send(sender=self.pid_, receiver=(Atom('erl@x1'), Atom('erlBridge')), message=(self.pid_, (Atom('acc'), (42, 43, 44))))


def main():
    global bp
    node = Pyrlang.Node("py@rpi3", "Cookie42")
    node.start()
    # this automatically schedules itself to run via gevent
    bp = MyProcess(node)
    gevent.sleep(0.1)
    gevent.sleep(0.1)
    gevent.sleep(0.1)
    gevent.sleep(1.1)
    bp.sendTest()
    #while True:
    listener()

if __name__ == "__main__":
    main()
