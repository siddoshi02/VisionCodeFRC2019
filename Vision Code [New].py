#!/usr/bin/env python3


import json
import time
import sys
import numpy as np
import math
import cv2

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

CAMERA_WIDTH = 640
FOV = 60
DEG_PER_PIXEL = FOV/CAMERA_WIDTH

def getImageSizeInDeg(width):
    nPixels = width
    return (nPixels * DEG_PER_PIXEL)

def getTargetDistance(width):
    radian = math.radians(getImageSizeInDeg(width))
    distance = ((5.125) / (math.tan(radian)))
    return distance

# def ScaleHeight(height):
 
def TrackTheTape(frame, sd): # does the opencv image proccessing

    try:
        HL = sd.getNumber('HL', 0)
        HU = sd.getNumber('HU', 57)
        SL = sd.getNumber('SL', 0)
        SU = sd.getNumber('SU', 167)
        VL = sd.getNumber('VL', 94)
        VU = sd.getNumber('VU', 255)
        TapeLower = (HL,SL,VL)
        TapeUpper = (HU,SU,VU)
        print("HSV lower:%s HSV Upper:%s" % (TapeLower, TapeUpper))
    except:
        print("Unable to grab network table values, going to default values")

    if frame is None: # if there is no frame recieved
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # creates a binary image with only the parts within the bounds True

    mask = cv2.inRange(hsv, TapeLower, TapeUpper) # cuts out all the useless stuff
    mask = cv2.erode(mask, None, iterations = 2)
    mask= cv2.dilate(mask, None, iterations = 2)

    minArea = 30 # minimum area of either of the tapes
    a, cnts , b= cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    center = None
    neg = [-1,-1] # just a negative array to use when no tape is detected
    centerN = neg
    centerL = neg
    centerR = neg
    avgArea = 0
    cnts2 = []
    for cur in cnts:
        if cv2.contourArea(cur) >= minArea:
            cnts2.append(cur)
    cnts = cnts2

    if len(cnts) > 1: # if there is more than 1 contour
        sorted(cnts, key=cv2.contourArea, reverse=True) #sorts the array with all the contours so those with the largest area are first
        c = cnts[0] # c is the largest contour
        d = cnts[1] # d is the second largest contour
        rect = cv2.minAreaRect(c)
        boxL = cv2.boxPoints(rect)
        boxL = np.int0(boxL)
        # for these refer to https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        rect2 = cv2.minAreaRect(d)
        boxR = cv2.boxPoints(rect2)
        boxR = np.int0(boxR)
        # if len(cnts) > 1:
        #     centerL = FindCenter(boxL)
        #     centerR = FindCenter(boxR)
            if findSlope(boxL)<findSlope(boxR): # finds out which tape is on the left and right by comparing slopes
                centerL,centerR = centerR,centerL
                boxL,boxR = boxR,boxL
            avgArea = (cv2.contourArea(c) + cv2.contourArea(d))/2
            tape1 = centerL
            tape2 = centerR
            centerN[0] = (centerR[0]+centerL[0])/2
            centerN[1] = (centerR[1]+centerL[1])/2
            cv2.drawContours(img,[boxL],0,(0,0,255),2)
            cv2.drawContours(img,[boxR],0,(0,255,0),2)
        else:
            tape1 = neg
            tape2 = neg
            avgArea = -1
    elif len(cnts) == 1: # if there is 1 contour
        sorted(cnts, key=cv2.contourArea, reverse=True) #sorts the array with all the contours so those with the largest area are first
        c = cnts[0] # c is the largest contour
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        boxL = None
        boxR = None
        # for these refer to https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        # if len(cnts) >= 1:
        center = FindCenter(box)
        if findSlope(box)<=0: # if there is only one tape detects wheter it is on the left or right using the value of its slope
            centerR = center
            centerN = centerR
            centerL = neg
            boxR = box
            cv2.drawContours(img,[boxR],0,(0,255,0),2)
        else:
            centerL = center
            centerN = centerL
            centerR = neg
            boxL = box
            cv2.drawContours(img,[boxL],0,(0,0,255),2)
        avgArea = cv2.contourArea(c)
        tape1 = centerL
        tape2 = centerR
        # else:
        #     tape1 = neg
        #     tape2 = neg
        #     avgArea = -1

    else: # when no tape is detected put the neg array everywhere
        tape1 = neg
        tape2 = neg
        centerN = neg
        avgArea = -1

    sd.putNumberArray('tape1', tape1)
    sd.putNumberArray('tape2', tape2)
    sd.putNumberArray('centerN', centerN)
    sd.putNumber('avgArea', avgArea)
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
    # HL = SmartDashBoardValues.putNumber('HL', 66)
    # HU = SmartDashBoardValues.putNumber('HU', 141)
    # SL = SmartDashBoardValues.putNumber('SL', 105)
    # SU = SmartDashBoardValues.putNumber('SU', 255)
    # VL = SmartDashBoardValues.putNumber('VL', 70)
    # VU = SmartDashBoardValues.putNumber('VU', 200)

    SmartDashBoardValues.setPersistent("HL")
    SmartDashBoardValues.setPersistent("HU")
    SmartDashBoardValues.setPersistent("SL")
    SmartDashBoardValues.setPersistent("SU")
    SmartDashBoardValues.setPersistent("VL")
    SmartDashBoardValues.setPersistent("VU")

    #Start first camera
    print("Connecting to camera 0")
    cs = CameraServer.getInstance()
    cs.enableLogging()
    Camera = UsbCamera('Cam 0', 0)
    Camera.setResolution(640,480)
    cs.addCamera(Camera)

    print("connected")

    Camera = UsbCamera('Cam 1', 1)
    Camera.setResolution(640, 480)
    Camera.setFPS(60)
    Camera.setBrightness(2)
    Camera.setExposureManual(1)
    Camera.getProperty("auto_exposure").set(0)
    Camera.getProperty("exposure").set(1)
    mjpegServer = MjpegServer("serve_Cam 1", 1182)
    mjpegServer.setResolution(640, 480)
    mjpegServer.setSource(Camera)

    CvSink = cs.getVideo()
    outputStream = cs.putVideo("Processed Frames", 640, 480)

    #buffers to store img data
    img = np.zeros(shape=(640,480,3), dtype=np.uint8)

    # loop forever
    loopCount = 0
    while True:
        GotFrame, img = CvSink.grabFrame(img)
        if GotFrame  == 0:
            outputStream.notifyError(CvSink.getError())
            continue
        img = TrackTheTape(img, SmartDashBoardValues)
        outputStream.putFrame(img)