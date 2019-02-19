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


def FindCenter(box):
    """
        Returns a 2D array
    """
    center = [0, 0]
    for points in box:
        center[0] += points[0]
        center[1] += points[1]
    center[0] /= 4
    center[1] /= 4
    return center


def TrackTheTape(frame, sd):
    TapeLower= (70,55,45)
    TapeUpper = (95,255,255)
    try:
        HL = sd.getNumber('HLTape', 70)
        HU = sd.getNumber('HUTape', 95)
        SL = sd.getNumber('SLTape', 55)
        SU = sd.getNumber('SUTape', 255)
        VL = sd.getNumber('VLTape', 45)
        VU = sd.getNumber('VUTape', 255)
        TapeLower = (HLTape,SLTape,VLTape)
        TapeUpper = (HUTape,SUTape,VUTape)
        print("HSV lower:%s HSV Upper:%s" % (TapeLower, TapeUpper))
    except:
        print("Unable to grab network table values, going to default values")

    try:
        Auto = sd.getBoolean('AutoExp', False)
    except:
        Auto = False

    if frame is None:
        sd.putNumber('GettingFrameData',False)
    else:
        sd.putNumber('GettingFrameData',True)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


    mask = cv2.inRange(hsv, TapeLower, TapeUpper)
    # mask = cv2.erode(mask, None, iterations = 2)
    # mask= cv2.dilate(mask, None, iterations = 2)


    a, cnts , b= cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    center = None
    neg = [-1,-1]

    # for cur in cnts:
    #     rect = cv2.minAreaRect(cnts[cur])
    #     box = cv2.boxPoints(rect)
    #     box = np.int0(box)
    #     if cv2.contourArea(rect) < 5 or cv2.contourArea(rect) > 100:
    #         cnts.remove(cur)
    #
    # filtered = cnts
    # if len(cnts) > 2:
    #     filtered = [cnts[0], cnts[1]]
    # # filtered is len 2
    # if len(filtered) == 0:
    #     sd.putNumberArray('tape1', neg)
    #     sd.putNumberArray('tape2', neg)
    # else:
    #     if FindCenter(filtered[0])[0] > FindCenter(filtered[1])[0]:
    #         filtered[0], filtered[1] = filtered[1], filtered[0]
    #     if len(filtered) == 1:
    #         sd.putNumberArray('tape2', neg)
    #     for i in range(len(filtered)):
    #         cur = filtered[cur]
    #         rect = cv2.minAreaRect(cur)
    #         box = cv2.boxPoints(rect)
    #         box = np.int0(box)
    #         cv2.drawContours(img,[box],0,(0,255*(1-i),255*i),2)
    #         sd.putNumberArray('tape' + str(i+1), FindCenter(box))
    # return img


    if len(cnts) > 1:
        print("if len(cnts) worked")
        sorted(cnts, key=cv2.contourArea, reverse=True)

        c = cnts[0]
        d = cnts[1]
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        rect2 = cv2.minAreaRect(d)
        box2 = cv2.boxPoints(rect2)
        box2 = np.int0(box2)
        if cv2.contourArea(rect) > 10 and cv2.contourArea(rect2) > 10:
            cv2.drawContours(img,[box],0,(0,0,255),2)
            cv2.drawContours(img,[box2],0,(0,255,0),2)

            # ((x,y), radius) = cv2.minEnclosingCircle(c)
            # M = cv2.moments(c)
            # center = (int(M["m10"] / M["m00"]), int (M["m01"] / M["m00"]))
            print("worked till networking")
            if len(cnts) > 1:
                center1 = [0,0]
                for i in box:
                    center1[0] += i[0]
                    center1[1] += i[1]
                center1[0] = center1[0]/4
                center1[1] = center1[1]/4

                center2 = [0,0]
                for i in box2:
                    center2[0] += i[0]
                    center2[1] += i[1]
                center2[0] = center2[0]/4
                center2[1] = center2[1]/4
                if center1[0]>center2[0]:
                    sd.putNumberArray('tape1', center2)
                    sd.putNumberArray('tape2', center1)
                elif center1[0]<center2[0]:
                    sd.putNumberArray('tape1', center1)
                    sd.putNumberArray('tape2', center2)
                print("Entered values")
            elif len(cnts) >=1:
                center1 = [0,0]
                for i in box:
                    center1[0] += i[0]
                    center1[1] += i[1]
                center1[0] = center1[0]/4
                center1[1] = center1[1]/4
                sd.putNumberArray('tape1', box)
                sd.putNumberArray('tape2', neg)
            else:
                # sd.putNumberArray('tape1', neg)
                # sd.putNumberArray('tape2', neg)
                sd.putNumberArray('tape1', neg)
                sd.putNumberArray('tape2', neg)
                print("Entered value")
    else:
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

    #Start camera
    print("Connecting to camera")
    cs = CameraServer.getInstance()
    cs.enableLogging()
    Camera = UsbCamera('Cam 0', 0)
    Camera.setExposureManual(5)
    Camera.setResolution(160,120)
    cs.addCamera(Camera)

    print("connected")

    CvSink = cs.getVideo()
    outputStream = cs.putVideo("Processed Frames", 160,120)

    #buffer to store img data
    img = np.zeros(shape=(160,120,3), dtype=np.uint8)
    # loop forever
    while True:

        GotFrame, img = CvSink.grabFrame(img)
        if GotFrame  == 0:
            outputStream.notifyError(CvSink.getError())
            continue
        img = TrackTheTape(img, SmartDashBoardValues)

        outputStream.putFrame(img)
