#!/usr/bin/env python3

import json
import time
import sys
import numpy as np
import cv2


from cscore import CameraServer, VideoSource, CvSource, VideoMode, CvSink, UsbCamera
from networktables import NetworkTablesInstance

#   JSON format:
  # {
  #     "team": <team number>,
  #     "ntmode": <"client" or "server", "client" if unspecified>
  #     "cameras": [
  #         {
  #             "name": <camera name>
  #             "path": <path, e.g. "/dev/video0">
  #             "pixel format": <"MJPEG", "YUYV", etc>   // optional
  #             "width": <video mode width>              // optional
  #             "height": <video mode height>            // optional
  #             "fps": <video mode fps>                  // optional
  #             "brightness": <percentage brightness>    // optional
  #             "white balance": <"auto", "hold", value> // optional
  #             "exposure": <"auto", "hold", value>      // optional
  #             "properties": [                          // optional
  #                 {
  #                     "name": <property name>
  #                     "value": <property value>
  #                 }
  #             ]
  #         }
  #     ]
  # }

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
    TapeLower= (70,55,45) # the lower bounds of the hsv
    TapeUpper = (95,255,255) # the upper bounds of hsv values
    # try: # grabs values from the network table to dynamically change them
    #     HL = sd.getNumber('HLTape', 70)
    #     HU = sd.getNumber('HUTape', 95)
    #     SL = sd.getNumber('SLTape', 55)
    #     SU = sd.getNumber('SUTape', 255)
    #     VL = sd.getNumber('VLTape', 45)
    #     VU = sd.getNumber('VUTape', 255)
    #     TapeLower = (HLTape,SLTape,VLTape)
    #     TapeUpper = (HUTape,SUTape,VUTape)
    #     print("HSV lower:%s HSV Upper:%s" % (TapeLower, TapeUpper))
    # except:
    #     print("Unable to grab network table values, going to default values")

    try:
        Auto = sd.getBoolean('AutoExp', False)
    except:
        Auto = False

    if frame is None: # if there is no frame recieved
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # creates a binary image with only the parts within the bounds True


    mask = cv2.inRange(hsv, TapeLower, TapeUpper) # cuts out all the useless shit
    # mask = cv2.erode(mask, None, iterations = 2)
    # mask= cv2.dilate(mask, None, iterations = 2)

    minArea = 15 # minimum area of either of the tapes
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
        print("worked till networking")
        if cv2.contourArea(cnts[0]) > minArea or cv2.contourArea(cnts[1]) > minArea:
            if len(cnts) >= 2:
                centerL = FindCenter(box)
                centerR = FindCenter(box2)
                if centerL[0]>centerR[0]: # finds out which tape is on the left and right by comparing x coordinates
                    centerL,centerR = centerR,centerL
                    box,box2 = box2,box
                sd.putNumberArray('tape1', centerL)
                sd.putNumberArray('tape2', centerR)
            elif len(cnts) == 1:
                center = FindCenter(box)
                if center[0] < 80: # if there is only one tape detects wheter it is on the left or right
                    centerR = center
                    centerL = neg
                else:
                    centerL = center
                    centerR = neg
                sd.putNumberArray('tape1', centerL)
                sd.putNumberArray('tape2', centerR)
            else:
                # sd.putNumberArray('tape1', neg)
                # sd.putNumberArray('tape2', neg)
                sd.putNumberArray('tape1', neg)
                sd.putNumberArray('tape2', neg)
            cv2.drawContours(img,[box],0,(0,0,255),2)
            cv2.drawContours(img,[box2],0,(0,255,0),2)

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
    cs = CameraServer.getInstance()
    cs.enableLogging()
    Camera = UsbCamera('Cam 0', 0)
    Camera.setExposureManual(5)
    Camera.setResolution(160,120)
    cs.addCamera(Camera)

    print("connected")

    # Start second camera
    # print("Connecting to camera 1")
    # Camera1 = UsbCamera('Cam 1', 1)
    # Camera1.setResolution(160,120)
    # cs.addCamera(Camera1)
    #
    # print("connected")

    # CvSink1 = cs.getVideo()
    # outputStream1 = cs.putVideo("Processed Frames", 160,120)
    CvSink = cs.getVideo()
    outputStream = cs.putVideo("Processed Frames", 160,120)

    #buffers to store img data
    img = np.zeros(shape=(160,120,3), dtype=np.uint8)
    # img1 = np.zeros(shape=(160,120,3), dtype=np.uint8)
    # loop forever
    while True:

        GotFrame, img = CvSink.grabFrame(img)
        if GotFrame  == 0:
            outputStream.notifyError(CvSink.getError())
            continue
        img = TrackTheTape(img, SmartDashBoardValues)
        # GotFrame1, img1 = CvSink.grabFrame(img1)
        # if GotFrame1  == 0:
        #     outputStream.notifyError(CvSink.getError())
        #     continue
        # img1 = TrackTheTape(img1, SmartDashBoardValues)

        outputStream.putFrame(img)
        # outputStream1.putFrame(img1)
