#!/usr/bin/env python3

import json
import time
import sys
import numpy as np
import math
import cv2
import argparse
# import imutils
from collections import deque

from cscore import CameraServer, VideoSource, CvSource, VideoMode, CvSink, UsbCamera, CameraServer, MjpegServer
from networktables import NetworkTablesInstance

configFile = "/boot/frc.json"

class CameraConfig: pass

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

# returns an array of the center coordinates
def FindCenter(box):
    center = [0,0]
    for i in box:
        center[0] += i[0]
        center[1] += i[1]
    center[0] = center[0]/4
    center[1] = center[1]/4
    return center

def findDistance(c1,c2):
    return math.sqrt((math.pow(c1[0]-c2[0],2))+(math.pow(c1[1]-c2[1],2)))

def findSlope(box):

    if(findDistance(box[0],box[1])>findDistance(box[1],box[2])):
        if box[0][0]-box[1][0]==0:
            return 1
        else:
            return (box[0][1]-box[1][1])/(box[0][0]-box[1][0])
    else:
        if box[1][0]-box[2][0]==0:
            return 1
        else:
            return (box[1][1]-box[2][1])/(box[1][0]-box[2][0])

def findRatio(box):
    long = findDistance(box[2],box[3])
    short = findDistance(box[1],box[2])
    ratio = long/short
    if abs(ratio)<1:
        ratio = 1/ratio
    return ratio

def PrintBox(box):
    for i in box :
        print(i[0])
        print(i[1])

def TrackTheBall(frame, sd): # does the opencv image proccessing

    try:
        HL = sd.getNumber('HL', 26)
        HU = sd.getNumber('HU', 35)
        SL = sd.getNumber('SL', 71)
        SU = sd.getNumber('SU', 255)
        VL = sd.getNumber('VL', 53)
        VU = sd.getNumber('VU', 154)
        BallLower = (HL,SL,VL)
        BallUpper = (HU,SU,VU)
        print("HSV lower:%s HSV Upper:%s" % (BallLower, BallUpper))
    except:
        print("Unable to grab network table values, going to default values")

    if frame is None: # if there is no frame recieved
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    # frame = cv2.GaussianBlur(frame, (11,11), 0)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # creates a binary image with only the parts within the bounds True
    mask = cv2.inRange(hsv, BallLower, BallUpper) # cuts out all the useless stuff
    mask = cv2.erode(mask, None, iterations = 2)
    mask= cv2.dilate(mask, None, iterations = 2)
    minArea = 1000 # minimum area of either of the ball
    a, cnts, b = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # cnts = imutils.grab_contours(cnts)
    center = None
    for j in range(5):
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            cnts.remove(c)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            if radius > 5:
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)            
	# neg = [-1,-1] # just a negative array to use when no tape is detected
    # sorted(cnts, key=cv2.contourArea, reverse=True)
    # cnts2 = []
    # for cur in cnts:
    #     if cv2.contourArea(cur) >= minArea:
    #         cnts2.append(cur)
    # cnts = cnts2
    # cv2.drawContours(img,cnts,-1,(0,0,255),2)
    # detector = cv2.SimpleBlobDetector()
    # for i in cnts:
    #     sd.putNumberArray('Ball', i);
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

    #Start first camera
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
    Camera.getProperty("saturation").set(7)
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
