import cv2
import matplotlib.pyplot as plt
from PIL import Image
import argparse
from pathlib import Path
from multiprocessing import Process, Pipe, Value, Array
import torch
from config import get_config
from mtcnn import MTCNN
from Learner import face_learner
from utils import load_facebank, draw_box_name, prepare_facebank
import matplotlib.pyplot as plt
import glob
import os
import numpy as np

parser = argparse.ArgumentParser(description='for face verification')
parser.add_argument("-s", "--save", help="whether save", action="store_true")
parser.add_argument('-th', '--threshold',
                    help='threshold to decide identical faces', default=1.5, type=float)
parser.add_argument(
    "-u", "--update", help="whether perform update the facebank", action="store_false")
parser.add_argument(
    "-tta", "--tta", help="whether test time augmentation", action="store_true")
parser.add_argument(
    "-c", "--score", help="whether show the confidence score", action="store_true")
args = parser.parse_args()

conf = get_config(False)

mtcnn = MTCNN()
print('arcface loaded')

data_folder_root = os.path.dirname(os.path.abspath(__file__))

learner = face_learner(conf, True)
learner.threshold = args.threshold
if conf.device.type == 'cpu':
    learner.load_state(conf, 'cpu_final.pth', True, True)
else:
    learner.load_state(conf, 'final.pth', True, True)
learner.model.eval()
print('learner loaded')

if args.update:
    targets, names = prepare_facebank(conf, learner.model, mtcnn, tta=args.tta)
    print('facebank updated')
else:
    targets, names = load_facebank(conf)
    print('facebank loaded')

# # inital camera
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)


def main():

    while cap.isOpened():
        isSuccess, frame = cap.read()
        match_score = None
        name = None
        det_image = None
        if isSuccess:
            try:
                #                 image = Image.fromarray(frame[...,::-1]) #bgr to rgb
                image = Image.fromarray(frame)
                # image = image.resize((500,500))
                bboxes, faces = mtcnn.align_multi(
                    image, conf.face_limit, conf.min_face_size)
                # shape:[10,4],only keep 10 highest possibiity faces
                bboxes = bboxes[:, :-1]
                bboxes = bboxes.astype(int)
                bboxes = bboxes + [-1, -1, 1, 1]  # personal choice
                results, score = learner.infer(conf, faces, targets, args.tta)
                # print(score)
               # print(score[0])
                match_score = "{:.2f}".format(score.data[0]*100)
                # print(x)
                for idx, bbox in enumerate(bboxes):
                    if args.score:
                        frame = draw_box_name(
                            bbox, names[results[idx] + 1] + '_{:.2f}'.format(score[idx]), frame)
                    else:
                        if float('{:.2f}'.format(score[idx])) > .98:
                            match_score = None
                            # name = names[0]
                            # print(name)
                            frame = draw_box_name(bbox, "unknown", frame)
                        else:
                            name = names[results[idx]+1]
                            match_score = match_score
                            frame = draw_box_name(
                                bbox, names[results[idx] + 1], frame)

                            path = "/home/circle/Downloads/work-care-master/engine/dl/data/facebank" + \
                                str(name)+"/*.jpg"
                            filenames = [img for img in glob.glob(path)]
                            img = cv2.imread(filenames[0])
                            det_image = cv2.imencode('.jpg', img)[1].tostring()

            except:
                pass
                # print('detect error')
            ret, jpeg = cv2.imencode('.jpg', frame)

            return jpeg.tostring(), det_image, name, match_score

