import numpy as np
import cv2
import json

def dict_concate(d):
    output = {}
    for i in d:
        for k in i.keys():
            if k not in output:
                output[k] = []
            output[k].append(i[k])
    return output

def rotate(p, origin=(0, 0), angle=0):
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])
    o = np.atleast_2d(origin)
    p = np.atleast_2d(p)
    return np.squeeze((R @ (p.T-o.T) + o.T).T) 

def padding_zero(i,n=5):
    i = str(i)
    if len(i)<n:
        return "0"*(n-len(i))+i
    else:
        return i
       
      
def draw_box(anno_path):
    img_path = anno_path.replace(".json",".jpg")
    img = cv2.imread(img_path)
    with open(anno_path,"r",encoding="utf-8") as file:
        anno = json.load(file)
    cls_list = []
    bbox_list = []

    for a in anno['labels']:
        if a['label_type']=='bbox':
            for i in a['object']:
                cls_list.append(i['class'])
                x1,y1,x2,y2 = i['x1'],i['y1'],i['x2'],i['y2']
                bbox_list.append([x1,y1,x2,y2])
            for c,b in zip(cls_list,bbox_list):
                x1,y1,x2,y2 = b
                cv2.rectangle(img,(int(x1),int(y1)),(int(x2),int(y2)),(255,0,0),5)
                text_center_x, text_center_y= int((x1+x2)/2), int((y1+y2)/2)
                cv2.putText(img, str(c), (text_center_x,text_center_y), cv2.FONT_HERSHEY_SIMPLEX,
              0.5, (0, 0, 255), 1, cv2.LINE_AA) 
        elif a['label_type']=="rbbox":
            for i in a['object']:
                cls_list.append(i['class'])
                x,y,w,h,a = i['x'],i['y'],i['w'],i['h'],i['a']
                four_points = np.array([[x-0.5*w,y-0.5*h],[x+0.5*w,y-0.5*h],[x-0.5*w,y+0.5*h],[x+0.5*w,y+0.5*h]])
                new_four_points = rotate(four_points, origin=(x,y), angle=a)
                bbox_list.append(new_four_points)
            for c,b in zip(cls_list,bbox_list):
                p1,p2,p3,p4 = [tuple(int(j) for j in i) for i in [b[0],b[1],b[2],b[3]]]
                cv2.line(img,p1,p2,(255,0,0),20)
                cv2.line(img,p1,p3,(255,0,0),20)
                cv2.line(img,p2,p4,(255,0,0),20)
                cv2.line(img,p3,p4,(255,0,0),20)
                text_center_x, text_center_y= int((p1[0]+p4[0])/2), int((p1[1]+p4[1])/2)
                text_center_x -= int(cv2.getTextSize(c,cv2.FONT_HERSHEY_COMPLEX,2,5)[0][0]/2)
                cv2.putText(img, str(c), (text_center_x,text_center_y), cv2.FONT_HERSHEY_SIMPLEX,
              2, (0, 0, 255), 5, cv2.LINE_AA)
    return img