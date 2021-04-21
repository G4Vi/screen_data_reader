#!/usr/bin/env python2
#https://www.pixilart.com/draw
#https://towardsdatascience.com/extracting-circles-and-long-edges-from-images-using-opencv-and-python-236218f0fee4
#https://maker.pro/raspberry-pi/tutorial/grid-detection-with-opencv-on-raspberry-pi
#https://www.pyimagesearch.com/2014/04/21/building-pokedex-python-finding-game-boy-screen-step-4-6/
#https://www.pyimagesearch.com/2014/05/05/building-pokedex-python-opencv-perspective-warping-step-5-6/
import cv2
import numpy as np
import sys
import zlib
print(cv2.__version__)

image = cv2.imread("test_images/box2.png")
image = cv2.imread("test_images/boxbad.jpg")
image = cv2.imread("test_images/unmodified3.PNG")
#image = cv2.imread("test_images/real4.PNG")
#image = cv2.imread("test_images/header.PNG")

cv2.imshow("Image", image)
cv2.waitKey()
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
cv2.imshow("gray", gray)
cv2.waitKey()

grayfilter = cv2.bilateralFilter(gray, 11, 17, 17)
edged = cv2.Canny(grayfilter, 30, 200)
cv2.imshow("edged", edged)
cv2.waitKey()
contours, hierarchy = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

#blur = cv2.GaussianBlur(gray, (5,5), 0)
#thresh = cv2.adaptiveThreshold(blur, 255, 1, 1, 11, 2)
#contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


#print(contours)
max_area = 0
c = 0
cnt = 0
for i in contours:
        area = cv2.contourArea(i)
        #if (area > 1000):         
        if (area > max_area) and (area > 1000):
            print("area " + str(area))
            max_area = area
            cnt = i
            print("drawing")
            imcopy = image.copy()
            cv2.drawContours(imcopy, contours, c, (0, 255, 0), 3)
            cv2.imshow("contours", imcopy)
            cv2.waitKey()
                    
        c+=1


# simplify contour to 4 point rect
peri = cv2.arcLength(cnt, True)
approx = cv2.approxPolyDP(cnt, 0.015 * peri, True)
print('apprx')
print(approx)
cnt = approx

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
cv2.imshow('warp', warp)
cv2.waitKey()

# convert to black and white
(thresh, bg) = cv2.threshold(warp, 50, 255, cv2.THRESH_BINARY)
cv2.imshow("bg ", bg)
cv2.waitKey()

# remove frame
x = 0
y = 0
w = warp.shape[1]
h = warp.shape[0]
print('w ' + str(w) + ' h' + str(h))
wexpt = 8
worg = 10
hexpt = 8
horg = 10
wexpt = 75
worg = 77
hexpt = 49
horg = 51

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
cv2.imshow("roi ", roi)
cv2.imwrite('dump/roi.png', roi)
cv2.waitKey()

# read the bits
mybits = []
for ypix in range(0, hexpt):
    acty = int((ypix + 0.5)*hscale)
    for xpix in range(0, wexpt):
        actx = int((xpix + 0.5) * wscale)
        pixel = roi[acty, actx]
        print(' x ' + str(actx) + ' y ' + str(acty) + ' : '+str(pixel))
        mybits.append((~pixel) & 1)

# abort if the wrong number of bits were read somehow
if len(mybits) != (wexpt * hexpt):
    print("Incorrect number of bits read")
    sys.exit(1)

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

# extract size
sizebits  = mybits[0:16]
sizebytes = bits2bytes(sizebits)
size      = sizebytes[0] | (sizebytes[1] << 8)
print(len(sizebits))
print('size ' + str(size))

# extract data
dataend = (wexpt * hexpt)-32
databits = mybits[16:dataend]
print(len(databits)) 
databytes = bits2bytes(databits)
print(len(databytes))
f = open("dump/data.txt", "wb")
f.write(databytes)
f.close()

# extract the checksum
checkin = (wexpt * hexpt)-32
checkbits = mybits[checkin:(wexpt * hexpt)]
print(len(checkbits)) 
checkbytes = bits2bytes(checkbits)
checksum = checkbytes[0] | (checkbytes[1] << 8) | (checkbytes[2] << 16) | (checkbytes[3] << 24)
print('read checksum ' + hex(checksum))
calcchk = zlib.crc32(bytes(databytes))
calcchk &= 0xffffffff
print('calc checksum ' + hex(calcchk))

# verify the checksum matches
if checksum != calcchk:
    print("checksum doesn't match")
    sys.exit(1)
