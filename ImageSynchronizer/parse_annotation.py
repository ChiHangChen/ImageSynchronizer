import json
import cv2
import pandas as pd
import sys, glob, os
from ImageSynchronizer.utils import dict_concate, rotate, padding_zero
from jinja2 import Template
import numpy as np
import base64
import shutil
import pkg_resources


class AnnotationError(Exception):
    def __init__(self,v):
        self.message = f"Annotaion version {v} is not supported."
    def __str__(self):
        return self.message
    
class parse_annotation():    
    def __init__(self, anno_path):
        self.__anno_path = anno_path
        with open(anno_path,"r",encoding='utf-8') as f:
            self.content = json.load(f)
        if self.content['anno_version']!='0.2.0':
            raise AnnotationError(self.content['anno_version'])
            
        for i in self.content['labels']:
            if i['label_type'] in ['bbox','rbbox']:
                self.objects_df = pd.DataFrame(i['object'])
                self.label_type =  i['label_type']
                break
        
        
    def __rbbox_point_convert(self, r):
        four_points = np.array([
            [r['x']-0.5*r['w'],r['y']-0.5*r['h']],
            [r['x']+0.5*r['w'],r['y']-0.5*r['h']],
            [r['x']-0.5*r['w'],r['y']+0.5*r['h']],
            [r['x']+0.5*r['w'],r['y']+0.5*r['h']]
        ])
        new_four_points = rotate(four_points, origin=(r['x'],r['y']), angle=r['a'])
        return new_four_points
      
    def __create_labelme_json(self,shape_type):
        json_data = {}
        shapes = []
        if shape_type=='polygon':
            convert_points = self.objects_df.apply(self.__rbbox_point_convert, axis=1)
            for j,point in enumerate(convert_points):
                shape = {}
                shape['label'] = self.objects_df['class'][j]
                shape['line_color'] = None
                shape['fill_color'] = None
                points = []
                for x, y in [point[0], point[1], point[3], point[2]]:
                    points.append([x, y])
                shape['points'] = points
                shape['shape_type'] = 'polygon'
                shapes.append(shape)
        elif shape_type=='rectangle':
            for j in range(len(self.objects_df)):
                shape = {}
                shape['label'] = self.objects_df['class'][j]
                shape['line_color'] = None
                shape['fill_color'] = None
                shape['points'] = [[self.objects_df['x1'][j],self.objects_df['y1'][j]],[self.objects_df['x2'][j],self.objects_df['y2'][j]]]
                shape['shape_type'] = 'rectangle'
                shapes.append(shape)
        img_path = self.__anno_path.replace(".json",".jpg")
        img = cv2.imread(img_path)
        image_data = open(img_path, 'rb').read()
        json_data['version'] = '3.16.7'
        json_data['flags'] = {}
        json_data['shapes'] = shapes
        json_data['lineColor'] = [0, 255, 0, 128]
        json_data['fillColor'] = [0, 255, 0, 128]
        json_data['imagePath'] = os.path.basename(img_path)
        json_data['imageData'] = base64.b64encode(image_data).decode('utf-8')
        json_data['imageHeight'] = img.shape[0]
        json_data['imageWidth'] = img.shape[1]     
        move_dir = os.path.join(os.path.dirname(self.__anno_path),"ImageSynchronizer_annotation")
        if not os.path.exists(move_dir):
            os.makedirs(move_dir)
        shutil.move(self.__anno_path,os.path.join(move_dir,os.path.basename(self.__anno_path)))
        with open(self.__anno_path, 'w') as outfile:
            json.dump(json_data, outfile, ensure_ascii=False, indent=2)
        print(f"Convert {os.path.basename(self.__anno_path)} complete!")
        
    def convert(self, target_format):
        # target_format : string , the target convert format desire
        # Acceptable format : ["labelme_json","rolabelimg_xml"]
        
        # convert rbbox to labelme_json
        if (target_format == 'labelme_json') and (self.label_type=='rbbox'):
            self.__create_labelme_json('polygon')
            return None
            
        # convert rbbox to rolabelimg_xml
        if (target_format == 'rolabelimg_xml') and (self.label_type=='rbbox'):
            writer = Writer(self.__anno_path)
            for r in range(self.objects_df.shape[0]):
                cx = self.objects_df['x'][r]
                cy = self.objects_df['y'][r]
                w = self.objects_df['w'][r]
                h = self.objects_df['h'][r]
                a = self.objects_df['a'][r]
                class_name = self.objects_df['class'][r]
                writer.addObject(cx,cy,w,h,a,class_name)
            writer.save(self.__anno_path.replace(".json",".xml"))
            print(f"Convert {os.path.basename(self.__anno_path)} complete!")
            return None
            
             
        # convert rbbox to rolabelimg_xml
        if (target_format == 'labelme_json') and (self.label_type=='bbox'):
            self.__create_labelme_json('rectangle')    
            return None
        print(f"Can not convert {self.label_type} into {target_format} format.")


class Writer:
    def __init__(self, annotation_path, database='Unknown', segmented=0):
        stream = pkg_resources.resource_stream(__name__, 'rbbox_template.xml')
        with stream as s:
            self.annotation_template = Template(s.read().decode())
        img_path = annotation_path.replace(".json",".jpg")
        height, width, depth = cv2.imread(img_path).shape
        self.template_parameters = {
            'path': img_path,
            'filename': os.path.basename(img_path).split(".")[-2],
            'folder': os.path.basename(os.path.dirname(img_path)),
            'width': width,
            'height': height,
            'depth': depth,
            'database': 'Unknown',
            'segmented': 0,
            'objects': []
        }
        
    def addObject(self, x, y, w, h, a, class_name, pose='Unspecified', truncated=0, difficult=0):
        self.template_parameters['objects'].append({
            'name': class_name,
            'cx': x,
            'cy': y,
            'w': w,
            'h': h,
            'angle':a,
            'pose': pose,
            'truncated': truncated,
            'difficult': difficult,
        })
        
    def save(self, annotation_path):
        with open(annotation_path, 'w') as file:
            content = self.annotation_template.render(**self.template_parameters)
            file.write(content)