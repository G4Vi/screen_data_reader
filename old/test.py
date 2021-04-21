#!/usr/bin/env python2
#https://www.pixilart.com/draw
#https://towardsdatascience.com/extracting-circles-and-long-edges-from-images-using-opencv-and-python-236218f0fee4
#https://maker.pro/raspberry-pi/tutorial/grid-detection-with-opencv-on-raspberry-pi
import cv2
import numpy as np
print(cv2.__version__)

image = cv2.imread("box2.png")
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
for i in contours:
        area = cv2.contourArea(i)
        print("area " + str(area))
        if area > 1000:
                if area > max_area:
                    max_area = area
                    best_cnt = i
                    cv2.drawContours(image, contours, c, (0, 255, 0), 3)
                    cv2.imshow("contours", image)
                    cv2.waitKey()
                    
        c+=1

mask = np.zeros((gray.shape),np.uint8)
cv2.drawContours(mask,[best_cnt],0,255,-1)
cv2.imshow("mask1", mask)
cv2.waitKey()
cv2.drawContours(mask,[best_cnt],0,0,2)
cv2.imshow("mask2", mask)
cv2.waitKey()
out = np.zeros_like(gray)
out[mask == 255] = gray[mask == 255]
cv2.imshow("New image", out)
cv2.waitKey()

val, thresholded = cv2.threshold(out, 20, 255, cv2.THRESH_BINARY)
cv2.imshow("thresholded", thresholded )
cv2.waitKey()

blur = cv2.GaussianBlur(out, (5,5), 0)
cv2.imshow("blur1", blur)
cv2.waitKey()

thresh = cv2.adaptiveThreshold(blur, 255, 1, 1, 11, 2)
cv2.imshow("thresh1", thresh)

cv2.waitKey()