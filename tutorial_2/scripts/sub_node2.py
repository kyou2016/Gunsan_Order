#!/usr/bin/env python
import rospy
from tutorial_2.msg import MyMsgs

NAME_TOPIC = '/msgs_talk'
NAME_NODE = 'sub_node2'

def callback(msgs):
    rospy.loginfo(msgs.x[1] + 2**msgs.y[1])

if __name__ == '__main__':
    rospy.init_node(NAME_NODE, anonymous=True)
    sub = rospy.Subscriber(NAME_TOPIC, MyMsgs, callback)
    rospy.spin()