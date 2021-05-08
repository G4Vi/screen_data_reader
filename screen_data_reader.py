#!/usr/bin/env python3

'''
MIT License

Copyright (c) 2021 Gavin Hayes and other screen_data_reader authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

#https://www.pixilart.com/draw
#https://towardsdatascience.com/extracting-circles-and-long-edges-from-images-using-opencv-and-python-236218f0fee4
#https://maker.pro/raspberry-pi/tutorial/grid-detection-with-opencv-on-raspberry-pi
#https://www.pyimagesearch.com/2014/04/21/building-pokedex-python-finding-game-boy-screen-step-4-6/
#https://www.pyimagesearch.com/2014/05/05/building-pokedex-python-opencv-perspective-warping-step-5-6/
import cv2
import numpy as np
import sys, getopt, os
import zlib
import mss
import statistics
print(cv2.__version__)

wexpt = 75
worg = 77
hexpt = 49
horg = 51
ratioorg = worg/horg


OUTFILE = ''
OUTDIR  = ''

def usage(code):
    print('readdata.py -o <outputfile>')
    print('readdata.py -d <outputdir>')
    sys.exit(code)

argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv,"ho:d:",["help", "outfile=","outdir="])
except getopt.GetoptError:        
    usage(2)
for opt, arg in opts:
    if opt in ("-h", "--help"):
        usage(0)
    elif opt in ("-o", "--outfile"):
        OUTFILE = arg
    elif opt in ("-d", "--outdir"):
        OUTDIR = arg    


print("ratioorg " + str(ratioorg))
sct = mss.mss()
# Part of the screen to capture
mon = sct.monitors[2]
monitor = {"top": mon["top"], "left": mon["left"], "width": 1920, "height": 1080, "mon" : mon}

def decodeImage(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #cv2.imshow("gray", gray)
    #cv2.waitKey()
    
    #grayfilter = cv2.bilateralFilter(gray, 11, 17, 17)
    #edged = cv2.Canny(grayfilter, 30, 200)
    #cv2.imshow("edged", edged)
    #cv2.waitKey()
    #contours, hierarchy = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, 1, 1, 11, 2)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    
    #print(contours)
    max_area = 0
    c = -1
    cnt = 0
    for i in contours:
        c+=1
        area = cv2.contourArea(i)
        if (area <= 1000):
            continue
        if (area <= max_area):
            continue
        # try to find rectangle
        peri = cv2.arcLength(i, True)
        approx = cv2.approxPolyDP(i, 0.015 * peri, True)
        if len(approx) != 4:
            continue
        print(approx)
        rot_rect = cv2.minAreaRect(approx)
        (center), (width,height), angle = rot_rect
        # greater than 45 means we rotated the wrong way to get width and height
        # assuming the photo was taken <= 45 degress off
        if angle > 45:
            th = height
            height = width
            width = th                     
        print('width ' + str(width) + ' height ' + str(height))        
        ratio = width/height
        print('ratio ' + str(ratio))
        # needs to be close to data frame ratio, but accommodate non-square pixels
        if abs(ratio-ratioorg) > 0.2:
            continue        
        print("area " + str(area))        
        max_area = area
        cnt = approx
        #imcopy = image.copy()
        #cv2.drawContours(imcopy, contours, c, (0, 255, 0), 3)
        #cv2.imshow("contours", imcopy)
        #cv2.waitKey()
    if isinstance(cnt, int):
        print("No RECT")
        return
    
    # now that we have our screen contour, we need to determine
    # the top-left, top-right, bottom-right, and bottom-left
    # points so that we can later warp the image -- we'll start
    # by reshaping our contour to be our finals and initializing
    # our output rectangle in top-left, top-right, bottom-right,
    # and bottom-left order
    pts = cnt.reshape(4, 2)
    rect = np.zeros((4, 2), dtype = "float32")
    # the top-left point has the smallest sum whereas the
    # bottom-right has the largest sum
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    # compute the difference between the points -- the top-right
    # will have the minumum difference and the bottom-left will
    # have the maximum difference
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    # multiply the rectangle by the original ratio
    #rect *= ratio
    
    # now that we have our rectangle of points, let's compute
    # the width of our new image
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    # ...and now for the height of our new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    # take the maximum of the width and height values to reach
    # our final dimensions
    maxWidth = max(int(widthA), int(widthB))
    maxHeight = max(int(heightA), int(heightB))
    # construct our destination points which will be used to
    # map the screen to a top-down, "birds eye" view
    dst = np.array([
    	[0, 0],
    	[maxWidth - 1, 0],
    	[maxWidth - 1, maxHeight - 1],
    	[0, maxHeight - 1]], dtype = "float32")
    # calculate the perspective transform matrix and warp
    # the perspective to grab the screen
    M = cv2.getPerspectiveTransform(rect, dst)
    warp = cv2.warpPerspective(gray, M, (maxWidth, maxHeight))
    #cv2.imshow('warp', warp)
    #cv2.waitKey()
    
    # convert to black and white
    (thresh, bg) = cv2.threshold(warp, 100, 255, cv2.THRESH_BINARY)
    #cv2.imshow("bg ", bg)
    #cv2.waitKey()
    
    # remove frame
    x = 0
    y = 0
    w = warp.shape[1]
    h = warp.shape[0]
    print('w ' + str(w) + ' h' + str(h))
    
    wscale = w / float(worg)
    hscale = h / float(horg)
    print('wscale ' + str(wscale) + ' hscale ' + str(hscale))
    
    neww = int(w * (float(wexpt)/worg))
    newh = int(h * (float(hexpt)/horg))
    newx = ((w - neww) / 2) + x
    newy = ((h - newh) / 2) + y
    newx = int(newx)
    newy = int(newy)
    print('x ' + str(x), 'y ' + str(y))
    print('newx ' + str(newx), 'newy ' + str(newy))
    
    print('neww ' + str(neww) + ' newh ' + str(newh))
    roi=bg[newy:newy+newh,newx:newx+neww]
    #cv2.imshow("roi ", roi)
    #cv2.imwrite('dump/roi.png', roi)
    #cv2.waitKey()
    
    # read the bits
    mybits = []
    if (int((hexpt-0.5)*hscale) >= len(roi)) or (int((wexpt-0.5)*wscale) >= len(roi[0])):
        print("image too small")
        return
    for ypix in range(0, hexpt):
        acty = int((ypix + 0.5)*hscale)         
        for xpix in range(0, wexpt):
            actx = int((xpix + 0.5) * wscale)
            pixel = roi[acty, actx]
            #print(' x ' + str(actx) + ' y ' + str(acty) + ' : '+str(pixel))
            mybits.append((~pixel) & 1)
    
    # abort if the wrong number of bits were read somehow
    if len(mybits) != (wexpt * hexpt):
        print("Incorrect number of bits read")
        return
    
    def bits2bytes(bits):        
        # convert bits to bytes    
        bytes = bytearray(len(bits)//8)
        i = 0
        for byte in range(0, len(bits)//8):
            bit = (byte * 8)
            byteval = bits[bit] << 0;
            byteval |= bits[bit+1] << 1;
            byteval |= bits[bit+2] << 2;
            byteval |= bits[bit+3] << 3;
            byteval |= bits[bit+4] << 4;
            byteval |= bits[bit+5] << 5;
            byteval |= bits[bit+6] << 6;
            byteval |= bits[bit+7] << 7;
    
            bytes[i] = byteval
            i += 1
        return bytes;
    
    def read_uint16(arraybits, index):
        bits = arraybits[index:(index+16)]
        thebytes = bits2bytes(bits)
        return thebytes[0] | (thebytes[1] << 8)

    def bytes2uint16(thebytes, index):
        return thebytes[index] | (thebytes[index+1] << 8)
    
    def decode_bits(mybits):
        # read size
        packetsize = read_uint16(mybits, 32)
        if packetsize == 0:
            print("invalid size")
            return        
        
        # convert to bytes for retrieving the header and data bytes
        readbytes = bits2bytes(mybits[0:((packetsize+6)*8)])

        # extract startindex
        startindex = bytes2uint16(readbytes, 0)
        print('startindex ' + str(startindex))
        
        # extract endindex
        endindex = bytes2uint16(readbytes, 2)
        print('endindex ' + str(endindex))
    
        if startindex > endindex:
            print("read invalid startindex")
            return       

        # extract the checksum
        checkin = (wexpt * hexpt)-32
        checkbits = mybits[checkin:(wexpt * hexpt)]
        print(len(checkbits)) 
        checkbytes = bits2bytes(checkbits)
        checksum = checkbytes[0] | (checkbytes[1] << 8) | (checkbytes[2] << 16) | (checkbytes[3] << 24)
        print('read checksum ' + hex(checksum))

        # calculate the checksum
        calcchk = zlib.crc32(bytes(readbytes))
        print('calc checksum ' + hex(calcchk))        
        
        # verify the checksum matches
        if checksum != calcchk:
            print("checksum doesn't match")
            #imcopy = image.copy()
            #cv2.drawContours(imcopy, [cnt], 0, (0, 255, 0), 3)
            #cv2.imshow("contours", imcopy)
            #f = open("dump/bad.txt", "wb")
            #f.write(databytes)
            #f.close()
            #cv2.waitKey()
            return

        # extract data
        databytes = readbytes[6:(packetsize+6)]
        return [startindex, endindex, databytes]
    
    decoded = decode_bits(mybits)
    if decoded:
        return decoded
    
    print("using slow method")
    # read the bits (slow)
    mybits = []
    pixset = bytearray(int(hscale)*int(wscale))
    for ypix in range(0, hexpt):
        acty = int(ypix*hscale)
        for xpix in range(0, wexpt):
            actx = int(xpix * wscale)            
            for they in range(0, int(hscale)):
                for thex in range(0, int(wscale)):
                    #print("thex " + str(thex) + ' they ' + str(they))
                    pixset[they*thex] = roi[they+acty, thex+actx]
            #print(' x ' + str(actx) + ' y ' + str(acty) + ' : '+str(pixel))
            pixel = statistics.mode(pixset)
            mybits.append((~pixel) & 1)
    
    # abort if the wrong number of bits were read somehow
    if len(mybits) != (wexpt * hexpt):
        print("Incorrect number of bits read")
        return
    print("broke out")
    return decode_bits(mybits)


#image = cv2.imread("test_images/box2.png")
#image = cv2.imread("test_images/boxbad.jpg")
#image = cv2.imread("test_images/unmodified3.PNG")
#image = cv2.imread("test_images/real4.PNG")
#image = cv2.imread("test_images/header.PNG")
#image = cv2.imread("test_images/ss.PNG")

#results = [None]
results = 0
while True:
    image = np.array(sct.grab(monitor))
    #cv2.imshow("Image", image)
    #cv2.waitKey()
    result = decodeImage(image)
    if type(result) == list:
        # initialize to endindex+1 elements
        if isinstance(results, int):
            results = [None] * (result[1]+1)
        if not results[result[0]]:
            print("frame: " + str(result[0]))
            results[result[0]] = result[2]
            if results.count(None) == 0:
                break
    if type(results) == list:
        for i in results:
            print('isNone ' + str(i is None))

# the firstframe just has the filename
filename = results.pop(0).decode("utf-8");
# the lastframe just has the data crc32 in little endian 
indatacrc32arr = results.pop();
indatacrc32 = indatacrc32arr[0]| (indatacrc32arr[1] << 8) | (indatacrc32arr[2] << 16) | (indatacrc32arr[3] << 24)

# verify the read crc32 matches the overall crc32 
thedata = b''.join(results)
calccrc32 = zlib.crc32(thedata)
if calccrc32 == indatacrc32:
    print('crc32 0x%X' % calccrc32)
else:
    print('crc32 mismatch, calculated 0x%X expected 0x%X' %(calccrc32, indatacrc32))

path = ''
if OUTFILE != '':
    path = OUTFILE
elif OUTDIR != '':
    path = os.path.join(OUTDIR, filename)
else:
    path = filename
print("dumping to " + path)
f = open(path, "wb")
#for buf in results:
#    f.write(buf)
f.write(thedata)
f.close()
