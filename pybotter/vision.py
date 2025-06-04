import cv2
import numpy as np
import os
from datetime import datetime
from .utils import *

@creation_log
class Vision:

    # properties
    needle_img = None
    needle_w = 0
    needle_h = 0
    method = None

    # constructor
    def __init__(self, needle_img_path, name = None, method=cv2.TM_CCOEFF_NORMED):
        # load the image we're trying to match
        # https://docs.opencv.org/4.2.0/d4/da8/group__imgcodecs.html
        self.name = name
        self.needle_img_path = needle_img_path
        self.needle_img = cv2.imread(self.needle_img_path, cv2.IMREAD_UNCHANGED)
        # Save the dimensions of the needle image
        self.needle_w = self.needle_img.shape[1]
        self.needle_h = self.needle_img.shape[0]
        # There are 6 methods to choose from:
        # TM_CCOEFF, TM_CCOEFF_NORMED, TM_CCORR, TM_CCORR_NORMED, TM_SQDIFF, TM_SQDIFF_NORMED
        self.method = method
    

    def find(self, haystack_img, threshold=1, convert_mode=None, debug=False):
        """
        Template matching function to find needle_img inside haystack_img.
        - convert_mode: cv2 color conversion flag (e.g., cv2.COLOR_BGR2GRAY)
        - debug_mode: 'rectangles', 'points', 'save', 'debug' to visualize results
        """
        # Check for valid haystack image
        if haystack_img is None:
            return []  # Return empty list instead of None for consistency
            
        # Optional conversion or enforce both haystack and needle as grayscale
        if convert_mode:
            haystack = cv2.cvtColor(haystack_img, convert_mode)
            needle = cv2.cvtColor(self.needle_img, convert_mode)
        else:
            # Force both to grayscale to avoid dimension mismatch
            haystack = cv2.cvtColor(haystack_img, cv2.COLOR_BGR2GRAY) if len(haystack_img.shape) == 3 else haystack_img
            needle = cv2.cvtColor(self.needle_img, cv2.COLOR_BGR2GRAY) if len(self.needle_img.shape) == 3 else self.needle_img

        # Force both to uint8 type
        haystack = haystack.astype(np.uint8)
        needle = needle.astype(np.uint8)

        # Safety check for template size
        if haystack.shape[0] < needle.shape[0] or haystack.shape[1] < needle.shape[1]:
            log("[ERROR]", "Needle image is larger than haystack.")
            return []

        # Now safe to match
        result = cv2.matchTemplate(haystack, needle, self.method)
        locations = np.where(result >= threshold)
        locations = list(zip(*locations[::-1]))

        rectangles = []
        for loc in locations:
            rect = [int(loc[0]), int(loc[1]), self.needle_w, self.needle_h]
            rectangles.append(rect)
            rectangles.append(rect)

        rectangles, _ = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)

        points = []
        for (x, y, w, h) in rectangles:
            center_x = x + int(w / 2)
            center_y = y + int(h / 2)
            points.append((center_x, center_y))

            if debug:
                color = (0, 255, 0)
                cv2.rectangle(haystack_img, (x, y), (x + w, y + h), color, 2)

        if debug:
            cv2.imshow('Matches', haystack_img)
            cv2.waitKey(1)

        # Optional scaling
        #points = [(int(x / 1.2234), int(y / 1.2234)) for x, y in points]
        points = [(int(x), int(y)) for x, y in points]
        self.points = points
        return points
