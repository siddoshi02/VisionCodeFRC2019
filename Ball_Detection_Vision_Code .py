#!/usr/bin/env python3

import json
import time
import sys
import numpy as np
import math
import cv2
import argparse
from collections import deque

from cscore import CameraServer, VideoSource, CvSource, VideoMode, CvSink, UsbCamera, CameraServer, MjpegServer
from networktables import NetworkTablesInstance

configFile = "/boot/frc.json"

class CameraConfig: pass
#Camera number can vary based on the model of the camera being used. 1 = Logitech C310, 2 = Microsoft Lifecam
camera_number = 2

team = 7539
server = False
cameraConfigs = []

"""Report parse error."""
def parseError(str):
    print("config error in '" + configFile + "': " + str, file=sys.stderr)

"""Read single camera configuration."""
def readCameraConfig(config):
    cam = CameraConfig()

    # name
    try:
        cam.name = config["name"]

    except KeyError:
        parseError("could not read camera name")
        return False

    # path
    try:
        cam.path = config["path"]
    except KeyError:
        parseError("camera '{}': could not read path".format(cam.name))
        return False

    cam.config = config

    cameraConfigs.append(cam)
    return True

"""Read configuration file."""
def readConfig():
    global team
    global server
    # parse file
    try:
        with open(configFile, "rt") as f:
            j = json.load(f)
    except OSError as err:
        print("could not open '{}': {}".format(configFile, err), file=sys.stderr)
        return False

    # top level must be an object
    if not isinstance(j, dict):
        parseError("must be JSON object")
        return False

    # team number
    try:
        team = j["team"]
    except KeyError:
        parseError("could not read team number")
        return False

    # ntmode (optional)
    if "ntmode" in j:
        str = j["ntmode"]
        if str.lower() == "client":
            server = False
        elif str.lower() == "server":
            server = True
        else:
            parseError("could not understand ntmode value '{}'".format(str))

    # cameras
    try:
        cameras = j["cameras"]
    except KeyError:
        parseError("could not read cameras")
        return False
    for camera in cameras:
        if not readCameraConfig(camera):
            return False

    return True


def TrackTheBall(frame, sd): # does the opencv image proccessing


    try:
        if camera_number == 1:
            HL = sd.getNumber('HL', 26)
            HU = sd.getNumber('HU', 35)
            SL = sd.getNumber('SL', 71)
            SU = sd.getNumber('SU', 255)
            VL = sd.getNumber('VL', 53)
            VU = sd.getNumber('VU', 154)
        elif camera_number == 2:
            HL = sd.getNumber('HL', 19)
            HU = sd.getNumber('HU', 41)
            SL = sd.getNumber('SL', 237)
            SU = sd.getNumber('SU', 255)
            VL = sd.getNumber('VL', 67)
            VU = sd.getNumber('VU', 135)
        BallLower = (HL,SL,VL)
        BallUpper = (HU,SU,VU)
        print("HSV lower:%s HSV Upper:%s" % (BallLower, BallUpper))
    except:
        print("Unable to grab network table values, going to default values")

    if frame is None: # if there is no frame recieved
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # creates a binary image with only the parts within the bounds True
    mask = cv2.inRange(hsv, BallLower, BallUpper) # cuts out all the useless stuff
    mask = cv2.erode(mask, None, iterations = 2)
    mask= cv2.dilate(mask, None, iterations = 2)
    a, cnts, b = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)#finds pixels grouped together
    sorted(cnts, key=cv2.contourArea, reverse=True)
    for j in range(0, len(cnts)):
        if len(cnts) > 0:
            c = cnts[j]
            ((x, y), radius) = cv2.minEnclosingCircle(c)#finds the circle in the contour
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            if radius > 10 :
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)#draws the circle around the co-ordinates on the output image
                cv2.circle(frame, center, 5, (0, 0, 255), -1)#draws the center of the circle onto the output image
    for i in cnts:
        sd.putNumberArray('Ball', i)
    return frame


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        configFile = sys.argv[1]

    # read configuration
    if not readConfig():
        sys.exit(1)

    # start NetworkTables to send to smartDashboard
    ntinst = NetworkTablesInstance.getDefault()

    print("Setting up NetworkTables client for team {}".format(team))
    ntinst.startClientTeam(7539)

    SmartDashBoardValues = ntinst.getTable('SmartDashboard')

    SmartDashBoardValues.setPersistent("HL")
    SmartDashBoardValues.setPersistent("HU")
    SmartDashBoardValues.setPersistent("SL")
    SmartDashBoardValues.setPersistent("SU")
    SmartDashBoardValues.setPersistent("VL")
    SmartDashBoardValues.setPersistent("VU")

    #Start camera
    print("Connecting to camera 1SSSS")
    cs = CameraServer.getInstance()
    cs.enableLogging()
    Camera = UsbCamera('Cam 0', 0)
    cs.addCamera(Camera)

    print("connected")

    fps = 60
    width, height = 480, 270

    Camera.setResolution(width, height)
    Camera.setFPS(fps)
    # Camera.getProperty("exposure_auto").set(1)
    Camera.getProperty("brightness").set(5)
    Camera.getProperty("gain").set(0)
    Camera.getProperty("contrast").set(5)
    if camera_number == 1:
        Camera.getProperty("saturation").set(7)
    elif camera_number == 2:
        Camera.getProperty("saturation").set(69)
    Camera.getProperty("exposure_absolute").set(6)

    mjpegServer = MjpegServer("serve_Cam 1", 1182)
    mjpegServer.setResolution(width, height)
    mjpegServer.setSource(Camera)

    CvSink = cs.getVideo()
    outputStream = cs.putVideo("Processed Frames", width, height)

    #buffers to store img data
    img = np.zeros(shape=(width,height,3), dtype=np.uint8)

    # loop forever
    loopCount = 0
    while True:
        GotFrame, img = CvSink.grabFrame(img)
        if GotFrame  == 0:
            outputStream.notifyError(CvSink.getError())
            continue
        img = TrackTheBall(img, SmartDashBoardValues)
        outputStream.putFrame(img)
