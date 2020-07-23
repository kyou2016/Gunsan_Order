#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import cv2
import os, rospkg
import numpy as np
import json

from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridgeError

from utils import BEVTransform, CURVEFit, draw_lane_img

class LINEDetector:

    def __init__(self):
        self.image_sub = rospy.Subscriber('/image_jpeg/compressed', CompressedImage, self.image_Callback)
        self.img_lane = None

    def image_Callback(self, msg):
        
        try:
            np_arr = np.array(np.fromstring(msg.data, np.uint8))
            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except CvBridgeError as e:
            print(e)
        
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # 주황색 차선, 흰색 차선 모두 검출되는 값 -> 실제 사용시 다른 값이 검출될 수 있음
        upper_lane = np.array([37, 255, 255])
        lower_lane = np.array([ 0,   0, 250])

        self.img_lane = cv2.inRange(img_hsv, lower_lane, upper_lane)
        # self.img_lane = cv2.cvtColor(self.img_lane, cv2.COLOR_GRAY2BGR)


if __name__ == '__main__':
    rp = rospkg.RosPack()

    currentPath = rp.get_path("lane_detection_example")

    # WeCar의 카메라의 파라미터 값을 적어놓은 json파일을 읽어와서 params_cam으로 저장
    with open(os.path.join(currentPath, 'sensor/sensor_params.json'), 'r') as fp:
        sensor_params = json.load(fp)

    params_cam = sensor_params["params_cam"]

    rospy.init_node('Line_Detector', anonymous=True)

    # WeCar의 카메라 이미지를 Bird Eye View 이미지로 변환하기 위한 클래스를 선언
    bev_trans = BEVTransform(params_cam=params_cam)
    # BEV로 변환된 이미지에서 추출한 포인트를 기반으로 RANSAC을 이용하여 차선을 예측하는 클래스를 선언
    pts_learner = CURVEFit(order=1)

    lane_detector = LINEDetector()

    rate = rospy.Rate(20)

    while not rospy.is_shutdown():

        if lane_detector.img_lane is not None:

            # 카메라 이미지를 BEV이미지로 변환
            img_bev = bev_trans.warp_bev_img(lane_detector.img_lane)
            # 카메라 이미지에서 차선에 해당하는 포인트들을 추출
            lane_pts = bev_trans.recon_lane_pts(lane_detector.img_lane)

            # 추출한 포인트를 기반으로 차선을 예측
            x_pred, y_pred_l, y_pred_r = pts_learner.fit_curve(lane_pts)

            # 예측한 차선을 Path로 변환하여 메세지의 데이터를 작성
            pts_learner.write_path_msg(x_pred, y_pred_l, y_pred_r)
            # 예측한 차선을 publish topic: /lane_path
            pts_learner.pub_path_msg()

            # 예측한 차선 포인트들을 이미지에 넣기 위해서 변환
            xyl, xyr = bev_trans.project_lane2img(x_pred, y_pred_l, y_pred_r)

            # 예측한 차선 포인트들을 BEV이미지에 넣기
            img_bev_line = draw_lane_img(img_bev, xyl[:, 0].astype(np.int32),   # 예측한 차선 포인트들을 BEV이미지에 출력
                                                  xyl[:, 1].astype(np.int32),
                                                  xyr[:, 0].astype(np.int32),
                                                  xyr[:, 1].astype(np.int32),
                                                  )
            
            cv2.imshow('BEV Window', img_bev_line)
            cv2.waitKey(1)

            rate.sleep()