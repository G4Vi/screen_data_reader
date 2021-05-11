 #bg = cv2.adaptiveThreshold(warp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 401, 2)
        #(thresh, bg) = cv2.threshold(warp, 225, 255, cv2.THRESH_BINARY)        
        #if laststart == 16:
        #cv2.imshow("warp", warp)
        #cv2.waitKey()
        #cv2.imshow("bg", bg)
        #cv2.waitKey()
        #bg = cv2.adaptiveThreshold(warp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 401, 2)
        #(thresh, bg) = cv2.threshold(warp, 200, 255, cv2.THRESH_BINARY)

        wblur = cv2.GaussianBlur(warp, (5,5), 0)
        #cv2.imshow("blur", wblur)
        #cv2.waitKey()
        
        sigma = 0.23
        v = np.median(wblur)
        l = int(max(0, (1.0 - sigma) * v))
        u = int(min(255, (1.0 + sigma) * v))
        #bg = cv2.Canny(wblur, l, u)
        bg = cv2.Canny(wblur, 50, 255)
        #cv2.imshow("new", bg)
        #cv2.waitKey()

        kernel = np.ones((5,5),np.uint8)
        dilate = cv2.dilate(bg,kernel,iterations = 1)
        #cv2.imshow("dilate", dilate)
        #cv2.waitKey()

        kernel = np.ones((5,5),np.uint8)
        erode = cv2.erode(dilate,kernel,iterations = 1)
        #cv2.imshow("erode", erode)
        #cv2.waitKey()

        bg = erode          
        
        thecnts, heirachy = cv2.findContours(bg, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        #print('foundcnts ' + str(len(thecnts)))
        maxdepth = 0
        cindex = 0
        for acnt in thecnts:
            depth = 0
            checkindex = cindex
            while heirachy[0][checkindex][3] != -1:
                depth += 1
                checkindex = heirachy[0][checkindex][3]
            if depth > maxdepth:
                maxdepth = depth
            cindex += 1
        #if (maxdepth % 2) != 0:
        #    continue
        wcopy = warp.copy()
        #wcopy = cv2.cvtColor(warp,cv2.COLOR_GRAY2RGB)
        iswhite = 1       
        for lvl in range(0, maxdepth+1):
            if (lvl % 2):
                cindex = 0
                for acnt in thecnts:
                    if (cv2.contourArea(acnt) <= 2):
                        cindex += 1
                        continue
                    checkindex = cindex
                    depth = 0
                    while heirachy[0][checkindex][3] != -1:
                        depth += 1
                        checkindex = heirachy[0][checkindex][3]
                    if depth == lvl:
                        if iswhite:
                            cv2.fillPoly(wcopy, [acnt], (255, 255, 255))
                        else:
                            cv2.fillPoly(wcopy, [acnt], (0, 0, 0))
                    cindex += 1
                iswhite = not iswhite
        
        (thresh, bg) = cv2.threshold(wcopy, 254, 255, cv2.THRESH_BINARY)
        #cv2.imshow("edges", bg)
        #cv2.waitKey()   
            #wcopy = cv2.cvtColor(warp,cv2.COLOR_GRAY2RGB)
            #cindex = 0
            #for acnt in thecnts:
            #    depth = 0
            #    checkindex = cindex
            #    while heirachy[0][checkindex][3] != -1:
            #        depth += 1
            #        checkindex = heirachy[0][checkindex][3]
            #    white = (depth % 2)                    
            #    if (depth == 1):
            #        if white:
            #            cv2.fillPoly(wcopy, [acnt], (255, 255, 255))
            #        else:
            #            cv2.fillPoly(wcopy, [acnt], (0, 0, 0))
            #        #cv2.drawContours(wcopy, [acnt], 0, (0, 255, 0), 3)
            #        #                
            #    cindex += 1
            #cv2.imshow("edges", wcopy)
            #cv2.waitKey()   
            #cindex = 0
            #for acnt in thecnts:
            #    depth = 0
            #    checkindex = cindex
            #    while heirachy[0][checkindex][3] != -1:
            #        depth += 1
            #        checkindex = heirachy[0][checkindex][3]   
            #    white = not (depth % 2)                 
            #    if (depth == 3):
            #        if white:
            #            cv2.fillPoly(wcopy, [acnt], (255, 255, 255))
            #        else:
            #            cv2.fillPoly(wcopy, [acnt], (0, 0, 0))
            #        #cv2.drawContours(wcopy, [acnt], 0, (0, 255, 0), 3)
            #        #                
            #    cindex += 1
            #cv2.imshow("edges2", wcopy)
            #cv2.waitKey()           

            #adat = cv2.adaptiveThreshold(warp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 4001, 2)
            #cv2.imshow("adat", adat)
            #cv2.waitKey()
        #cv2.imshow("bg ", bg)
        #cv2.waitKey()
        if laststart == 16:
            pass
            #cv2.imshow('warp', warp)
            #cv2.waitKey()
            #cv2.imshow("bg ", bg)
            #cv2.waitKey()
            #(thresh, alt) = cv2.threshold(warp, 200, 255, cv2.THRESH_BINARY)
            #bg = alt 
            #cv2.imshow("alt ", alt)
            #cv2.waitKey()