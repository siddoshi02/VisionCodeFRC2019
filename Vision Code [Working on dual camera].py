#!/usr/bin/env python3

import json
import time
import sys
import numpy as np
import cv2

from cscore import CameraServer, VideoSource, CvSource, VideoMode, CvSink, UsbCamera
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

def TrackTheTape(frame, sd): # does the opencv image proccessing
    Exp = sd.getNumber('ExpAuto', 0)
    TapeLower= (65,75,75) # the lower bounds of the hsv
    TapeUpper = (80,255,255) # the upper bounds of hsv values
    if frame is None: # if there is no frame recieved
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # creates a binary image with only the parts within the bounds True

    mask = cv2.inRange(hsv, TapeLower, TapeUpper) # cuts out all the useless shit
    # mask = cv2.erode(mask, None, iterations = 2)
    # mask= cv2.dilate(mask, None, iterations = 2)

    minArea = 75 # minimum area of either of the tapes
    a, cnts , b= cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    center = None
    neg = [-1,-1] # just a negative array to use when no tape is detected
    if len(cnts) > 1: # if there is more than 1 contour
        sorted(cnts, key=cv2.contourArea, reverse=True) #sorts the array with all the contours so those with the largest area are first
        c = cnts[0] # c is the largest contour
        d = cnts[1] # d is the second largest contour
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        # for these refer to https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        rect2 = cv2.minAreaRect(d)
        box2 = cv2.boxPoints(rect2)
        box2 = np.int0(box2)
        if len(cnts) > 1:
            centerL = FindCenter(box)
            centerR = FindCenter(box2)
            if centerL[0]>centerR[0]: # finds out which tape is on the left and right by comparing x coordinates
                centerL,centerR = centerR,centerL
                box,box2 = box2,box
            sd.putNumberArray('tape1', centerL)
            sd.putNumberArray('tape2', centerR)
            cv2.drawContours(img,[box],0,(0,0,255),2)
            cv2.drawContours(img,[box2],0,(0,255,0),2)
        else:
            # sd.putNumberArray('tape1', neg)
            # sd.putNumberArray('tape2', neg)
            sd.putNumberArray('tape1', neg)
            sd.putNumberArray('tape2', neg)
    elif len(cnts) == 1: # if there is 1 contour
        sorted(cnts, key=cv2.contourArea, reverse=True) #sorts the array with all the contours so those with the largest area are first
        c = cnts[0] # c is the largest contour
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        # for these refer to https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        if len(cnts) >= 1:
            center = FindCenter(box)
            if center[0] < 80: # if there is only one tape detects wheter it is on the left or right
                centerR = center
                centerL = neg
                cv2.drawContours(img,[box],0,(0,255,0),2)
            else:
                centerL = center
                centerR = neg
                cv2.drawContours(img,[box],0,(0,0,255),2)
            sd.putNumberArray('tape1', centerL)
            sd.putNumberArray('tape2', centerR)
        else:
            # sd.putNumberArray('tape1', neg)
            # sd.putNumberArray('tape2', neg)
            sd.putNumberArray('tape1', neg)
            sd.putNumberArray('tape2', neg)

    else: # when no tape is detected put the neg array everywhere
        sd.putNumberArray('tape1', neg)
        sd.putNumberArray('tape2', neg)
    return img


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

    #Start first camera
    print("Connecting to camera 0")
    exp = 4
    cs = CameraServer.getInstance()
    cs.enableLogging()
    Camera = UsbCamera('Cam 0', 0)
    Camera.setExposureManual(exp)
    Camera.setResolution(160,120)
    cs.addCamera(Camera)
    print("connected")
    sp = SmartDashBoardValues
    sp.putNumber('ExpAuto', 0)
    CvSink = cs.getVideo()
    outputStream = cs.putVideo("Processed Frames", 160,120)

    #buffers to store img data
    img = np.zeros(shape=(160,120,3), dtype=np.uint8)
    ExpStatus = sp.getNumber('ExpAuto', 0)
    # loop forever
    while True:
        ExpAuto = sp.getNumber('ExpAuto', 0)
        if ExpAuto == 0:
            if ExpStatus == 1:
                Camera.setExposureManual(exp)
                ExpStatus = 0
            GotFrame, img = CvSink.grabFrame(img)
            if GotFrame  == 0:
                outputStream.notifyError(CvSink.getError())
                continue
            img = TrackTheTape(img, SmartDashBoardValues)

        elif ExpAuto == 1:
                if ExpStatus == 0:
                    Camera.setExposureAuto()
                    ExpStatus = 1
                neg = [-1,-1] # just a negative array to use when no tape is detected
                sp.putNumberArray('tape1', neg)
                sp.putNumberArray('tape2', neg)
                GotFrame, img = CvSink.grabFrame(img)
                if GotFrame  == 0:
                    outputStream.notifyError(CvSink.getError())
                    continue

        else:
            print("")
        outputStream.putFrame(img)
