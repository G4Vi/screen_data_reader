#!/usr/bin/env python2
#https://www.pixilart.com/draw
#https://towardsdatascience.com/extracting-circles-and-long-edges-from-images-using-opencv-and-python-236218f0fee4
#https://maker.pro/raspberry-pi/tutorial/grid-detection-with-opencv-on-raspberry-pi
import cv2
import numpy as np
print(cv2.__version__)

def crop_minAreaRect(img, rect):

    # rotate img
    angle = rect[2]
    rows,cols = img.shape[0], img.shape[1]
    M = cv2.getRotationMatrix2D((cols/2,rows/2),angle,1)
    img_rot = cv2.warpAffine(img,M,(cols,rows))

    # rotate bounding box
    rect0 = (rect[0], rect[1], 0.0) 
    box = cv2.boxPoints(rect0)
    pts = np.int0(cv2.transform(np.array([box]), M))[0]    
    pts[pts < 0] = 0

    # crop
    img_crop = img_rot[pts[1][1]:pts[0][1], 
                       pts[1][0]:pts[2][0]]

    return img_crop


#image = cv2.imread("box2.png")
image = cv2.imread("boxbad.jpg")
cv2.imshow("Image", image)
cv2.waitKey()
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
cv2.imshow("gray", gray)
cv2.waitKey()



blur = cv2.GaussianBlur(gray, (5,5), 0)
#cv2.imshow("blur", blur)
#cv2.waitKey()
thresh = cv2.adaptiveThreshold(blur, 255, 1, 1, 11, 2)
#cv2.imshow("thresh", thresh)
#cv2.waitKey()
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

max_area = 0
c = 0
cnt = 0
for i in contours:
        area = cv2.contourArea(i)            
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

#minarearect = cv2.minAreaRect(cnt)
#img_cropped = crop_minAreaRect(image, minarearect)
#cv2.imshow('cropped', img_cropped)
#cv2.waitKey()

x,y,w,h = cv2.boundingRect(cnt)
print('w ' + str(w) + ' h' + str(h))

#mar = cv2.minAreaRect(cnt)
#print(mar)
#rotated = cv2.rotate(image, mar[2])
#cv2.imshow("Rotated (Correct)", rotated)
#cv2.waitKey()

wexpt = 8
worg = 10
hexpt = 8
horg = 10
wscale = w / float(worg)
hscale = h / float(horg)
wpixo = 1;
hpixo = 1;
wpix = float(wscale * wpixo) / 2
hpix = float(hscale * hpixo) / 2


neww = int(w * (float(wexpt)/worg))
newh = int(h * (float(hexpt)/horg))
newx = ((w - neww) / 2) + x
newy = ((h - newh) / 2) + y

print('neww ' + str(neww) + ' newh' + str(newh))
#roi=image[newy:newy+newh,newx:newx+neww]
(thresh, bg) = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

# display bounding rect
drawing = image.copy()
color = (0, 255, 0)
boundrect = cv2.rectangle(drawing, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
cv2.imshow("boundrect ", drawing)
cv2.waitKey()

roi=bg[newy:newy+newh,newx:newx+neww]

#cv2.imwrite('new.png', roi)
cv2.imshow("roi ", roi)
cv2.waitKey()
mybits = []
for ypix in range(0, 8):
    acty = int((ypix * hscale) + hpix)
    for xpix in range(0, 8):
        actx = int((xpix * wscale) + wpix)
        pixel = roi[acty, actx]
        print(' x ' + str(actx) + ' y ' + str(acty) + ' : '+str(pixel))
        mybits.append((~pixel) & 1)
for byte in range(0, len(mybits)/8):
    bit = (byte * 8)
    byteval = mybits[bit] << 0;
    byteval |= mybits[bit+1] << 1;
    byteval |= mybits[bit+2] << 2;
    byteval |= mybits[bit+3] << 3;
    byteval |= mybits[bit+4] << 4;
    byteval |= mybits[bit+5] << 5;
    byteval |= mybits[bit+6] << 6;
    byteval |= mybits[bit+7] << 7;
    print('byteval ' + str(byteval))


#print(str(x) + ' ' + str(y) + ' ' + str(w) + ' ' + str(h))
#cv2.rectangle(image,(x,y),(x+w,y+h),(0,255,0),2)
#cv2.imshow("Show",image)
#cv2.waitKey()
#cv2.destroyAllWindows()