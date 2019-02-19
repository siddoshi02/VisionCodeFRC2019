#!/usr/bin/env python3
#----------------------------------------------------------------------------
# Copyright (c) 2018 FIRST. All Rights Reserved.
# Open Source Software - may be modified and shared by FRC teams. The code
# must be accompanied by the FIRST BSD license file in the root directory of
# the project.
#----------------------------------------------------------------------------

import json
import time
import sys
import numpy as np
from cscore import CameraServer, VideoSource
# from networktables import NetworkTablesInstance
from networktables import NetworkTables
import cv2


def visionFun(image):
    try:
        lower = [0, 150, 130]
        upper = [255, 255, 255]

        lower = np.array(lower, dtype="uint8")
        upper = np.array(upper, dtype="uint8")

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)

        output = cv2.bitwise_and(image, image, mask=mask)

        ret,thresh = cv2.threshold(mask, 40, 255, 0)
        im2,contours,hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        firstLeft=False
        if len(contours) != 0:
            cv2.drawContours(output, contours, -1, 255, 3)
            cv2.drawContours(image, contours, -1, 255, 3)
            c = max(contours, key = cv2.contourArea)
            # print(c[0])
            # print(c[len(c)-1])
            # print(len(c))
            # print(c[563])
            x,y,w,h = cv2.boundingRect(c)
            cv2.rectangle(output,(x,y),(x+w,y+h),(0,255,0),2)
            cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                extLeft = tuple(c[c[:, :, 0].argmin()][0])
                extRight = tuple(c[c[:, :, 0].argmax()][0])
                if(extRight[1]>extLeft[1]):
                    firstLeft=False
                else:
                    firstLeft=True


                cY = int(M["m01"] / M["m00"])
            else:
                cX, cY = 0, 0
            cv2.circle(image, (cX, cY), 5, (255, 255, 255), -1)
            cv2.putText(image, "centroid", (cX - 25, cY - 25),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            sumX=cX
            sumY=cY
            contours=sorted(contours, key=cv2.contourArea)

            if M["m00"] != 0:

                extLeft = tuple(contours[-2][contours[-2][:, :, 0].argmin()][0])
                extRight = tuple(contours[-2][contours[-2][:, :, 0].argmax()][0])
                if(extRight[1]>extLeft[1]):
                    done=False
                    counter=2
                    while(not done):
                        extLeft = tuple(contours[-counter][contours[-counter][:, :, 0].argmin()][0])
                        extRight = tuple(contours[-counter][contours[-counter][:, :, 0].argmax()][0])
                        if(extRight[1]<extLeft[1]):
                            done=True
                            x,y,w,h = cv2.boundingRect(contours[-counter])
                            cv2.rectangle(output,(x,y),(x+w,y+h),(0,255,0),2)
                            cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
                            M = cv2.moments(contours[-counter])
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                        counter+=1
                else:
                    x,y,w,h = cv2.boundingRect(contours[-2])
                    cv2.rectangle(output,(x,y),(x+w,y+h),(0,255,0),2)
                    cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
                    M = cv2.moments(contours[-2])
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    # print("right tilt for 2nd biggest")
                # print(extRight)
                # print(extLeft)

            else:
                cX, cY = 0, 0
            sumX+=cX
            sumY+=cY
            cv2.circle(image, (cX, cY), 5, (255, 255, 255), -1)
            cv2.putText(image, "centroid", (cX - 25, cY - 25),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.circle(image, (int(sumX/2), int(sumY/2)), 5, (255, 255, 255), -1)
            return image,[sumX/2,sumY/2]
    except Exception as e:
        print(e)
        # cv2.putText(image, "centroid", (int(sumX/2), int(sumY/2)),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)



# #   JSON format:
# #   {
# #       "team": <team number>,
# #       "ntmode": <"client" or "server", "client" if unspecified>
# #       "cameras": [
# #           {
# #               "name": <camera name>
# #               "path": <path, e.g. "/dev/video0">
# #               "pixel format": <"MJPEG", "YUYV", etc>   // optional
# #               "width": <video mode width>              // optional
# #               "height": <video mode height>            // optional
# #               "fps": <video mode fps>                  // optional
# #               "brightness": <percentage brightness>    // optional
# #               "white balance": <"auto", "hold", value> // optional
# #               "exposure": <"auto", "hold", value>      // optional
# #               "properties": [                          // optional
# #                   {
# #                       "name": <property name>
# #                       "value": <property value>
# #                   }
# #               ]
# #           }
# #       ]
# #   }



# class CameraConfig: pass

# team = None
# server = False
# cameraConfigs = []

# """Report parse error."""
# def parseError(str):
#     print("config error in '" + configFile + "': " + str, file=sys.stderr)

# """Read single camera configuration."""
# def readCameraConfig(config):
#     cam = CameraConfig()

#     # name
#     try:
#         cam.name = config["name"]
#     except KeyError:
#         parseError("could not read camera name")
#         return False

#     # path
#     try:
#         cam.path = config["path"]
#     except KeyError:
#         parseError("camera '{}': could not read path".format(cam.name))
#         return False

#     cam.config = config

#     cameraConfigs.append(cam)
#     return True

# """Read configuration file."""
# def readConfig():
#     global team
#     global server

#     # parse file
#     try:
#         with open(configFile, "rt") as f:
#             j = json.load(f)
#     except OSError as err:
#         print("could not open '{}': {}".format(configFile, err), file=sys.stderr)
#         return False

#     # top level must be an object
#     if not isinstance(j, dict):
#         parseError("must be JSON object")
#         return False

#     # team number
#     try:
#         team = j["team"]
#     except KeyError:
#         parseError("could not read team number")
#         return False

#     # ntmode (optional)
#     # if "ntmode" in j:
#     #     str = j["ntmode"]
#     #     if str.lower() == "client":
#     #         server = False
#     #     elif str.lower() == "server":
#     #         server = True
#     #     else:
#     #         parseError("could not understand ntmode value '{}'".format(str))

#     # cameras
#     try:
#         cameras = j["cameras"]
#     except KeyError:
#         parseError("could not read cameras")
#         return False
#     for camera in cameras:
#         if not readCameraConfig(camera):
#             return False

#     return True

# """Start running the camera."""
# def startCamera(config):
#     print("Starting camera '{}' on {}".format(config.name, config.path))
#     camera = CameraServer.getInstance().startAutomaticCapture(name=config.name, path=config.path)



#     return camera

if __name__ == "__main__":
    configFile = "/boot/frc.json"
    cam=CameraServer.getInstance().startAutomaticCapture(name="rPi Camera 0", path="/dev/video0")
    with open(configFile, "rt") as f:
        j = json.load(f)
    for camera in j["cameras"]:
        cam.setConfigJson(json.dumps(camera))
    output=CameraServer.getInstance().putVideo("output",640,480)
    vision=CameraServer.getInstance().putVideo("vision",640,480)
    NetworkTables.initialize(server="10.60.24.2")
    sd = NetworkTables.getTable("SmartDashboard")
    i = 0
    img=np.zeros(shape=(160,120,3),dtype=np.uint8)
    while True:
        # cam.get
        img=CameraServer.getInstance().getVideo(name="rPi Camera 0").grabFrame(img)

        try:
            image,coord=visionFun(img)
            sd.putNumber('x', coord[0])
            sd.putNumber('y', coord[1])
            vision.putFrame(image)
        except Exception as e:
            sd.putNumber('x', -1)
            vision.putFrame(img)
            sd.putNumber('y', -1)

        output.putFrame(img)
        sd.putNumber('robotTime', i)
        # time.sleep(1)
        i += 1
        # print(1)
    # time.sleep(1)
