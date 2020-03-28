from kivy.lang import Builder
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
import time
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.checkbox import CheckBox
from kivy.base import runTouchApp
import requests 
import simplejson as JSON 
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
import cv2
import numpy as np
import subprocess
import requests 
import simplejson as JSON 
import pytesseract
import urllib.request
import os

# Create both screens. Please note the root.manager.current: this is how
# you can control the ScreenManager from kv. Each screen has by default a
# property manager that gives you the instance of the ScreenManager used.

Builder.load_string("""
<MenuScreen>:
    BoxLayout:

<SettingsScreen>:
    BoxLayout:

<CameraScreen>:
    BoxLayout:
        orientation: 'vertical'
        Camera:
            id: camera
            index: 3
            play: True
        Button:
            text: 'Capture'
            size_hint_y: None
            height: '48dp'
            on_press: root.capture()
            on_release: root.manager.current = 'settings'
""")


class CameraScreen(Screen):
    def capture(self):
        '''
        Function to capture the images and give them the names
        according to their captured time and date.
        '''
        camera = self.ids['camera']
        camera.export_to_png(f"IMG_0.png")
        print("Captured")
        self.manager.current = "settings"

# Declare both screens
class MenuScreen(Screen):

    def on_enter(self):
        Clock.schedule_once(self.change_screen)

    def change_screen(self, dt):
        request_url  = "https://localhost:5001/AbsencesApi/GetGroupsCount"
        request = requests.get( request_url, verify=False )
        data = request.content 
        count = int(data.decode())
        f = open("count.txt","w") 
        f.write(str(count))
        f.close()
        # print( count )
        dropdown = DropDown()
        for index in range( count ):
            request_url  = "https://localhost:5001/AbsencesApi/GetGroup?group_id="+str( index + 1 )
            request = requests.get( request_url, verify=False )
            response = request.content 
            data =  response.decode() 
            group = JSON.loads( data )
            btn = Button(text=group["label"], size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: dropdown.select(btn.text))
            dropdown.add_widget(btn)

        mainbutton = Button(text='Groups', size_hint=(None, None))
        mainbutton.bind(on_release=dropdown.open)

        def X(instance , x) :
            # x is the label selected !!
            f = open("group.txt","w") 
            f.write( x ) 
            f.close()
            setattr( mainbutton, 'text', x)
            mainbutton.y = 50000
            self.manager.current = "camera"

        dropdown.bind( on_select=X )
        runTouchApp( mainbutton )


class SettingsScreen(Screen):
    check_ref = []

    def on_enter(self):
        Clock.schedule_once(self.change_screen)
    
    def change_screen(self, dt):
        # get the group label
        f = open("group.txt","r") 
        group_label = f.readline()
        f.close()
        box_extraction("IMG_1.jpg", "./Cropped/")
        request_url  = "https://localhost:5001/AbsencesApi/GetTotalStudents?group_label="+group_label
        request = requests.get( request_url, verify=False )
        data = request.content 
        count_group = int(data.decode())
        box_url = "Cropped/3.png"
    
        total = box_cropping( box_url , 7 )
        print(total)


        for student in total :
            student_name = total[0]
            i = 1
            for session in total[1:] :
                if session == 0 :
                    request_url = "https://lcoalhost:5001/AbsencesApi/AddAbsence?student_name=student_name&session_id="+str(i)+"&group_label="+group_label
                    request = requests.get( request_url, verify=False )
                i+=1
            
        
        # ****************************************************************
        # get students of a group        
        # for index in range( count_group ):
        #     checkbox = CheckBox( pos = ( 100, index*25 ), active=False, size_hint = (None, None) )
        #     self.check_ref.append( checkbox )
        #     label = Label( text=f"Hello {index}", pos=( 0, index*25),  size_hint = (None, None) )
        #     self.add_widget( checkbox )
        #     self.add_widget( label )
        



# Create the screen manager
sm = ScreenManager()
sm.add_widget(MenuScreen(name='menu'))
sm.add_widget(SettingsScreen(name='settings'))
sm.add_widget(CameraScreen(name='camera'))

class TestApp(App):

    def build(self):
        return sm



def sort_contours(cnts, method="left-to-right"):
    # initialize the reverse flag and sort index
    reverse = False
    i = 0

    # handle if we need to sort in reverse
    if method == "right-to-left" or method == "bottom-to-top":
        reverse = True

    # handle if we are sorting against the y-coordinate rather than
    # the x-coordinate of the bounding box
    if method == "top-to-bottom" or method == "bottom-to-top":
        i = 1

    # construct the list of bounding boxes and sort them from top to
    # bottom
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),key=lambda b: b[1][i], reverse=reverse))

    # return the list of sorted contours and bounding boxes
    return (cnts, boundingBoxes)


def url_to_image(url):
	# download the image, convert it to a NumPy array, and then read
	# it into OpenCV format
	resp = urllib.request.urlopen(url)
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, 0)
	# return the image
	return image

def box_extraction(img_for_box_extraction_path, cropped_dir_path):

    img = cv2.imread(img_for_box_extraction_path, 0)  # Read the image

    # img = url_to_image(img_for_box_extraction_path)

    (thresh, img_bin) = cv2.threshold(img, 128, 255,
                                      cv2.THRESH_BINARY | cv2.THRESH_OTSU)  # Thresholding the image
    img_bin = 255-img_bin  # Invert the image

    cv2.imwrite("./Temp/Image_bin.jpg",img_bin)
   
    # Defining a kernel length
    kernel_length = np.array(img).shape[1]//40
     
    # A verticle kernel of (1 X kernel_length), which will detect all the verticle lines from the image.
    verticle_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
    # A horizontal kernel of (kernel_length X 1), which will help to detect all the horizontal line from the image.
    hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
    # A kernel of (3 X 3) ones.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    # Morphological operation to detect verticle lines from an image
    img_temp1 = cv2.erode(img_bin, verticle_kernel, iterations=3)
    verticle_lines_img = cv2.dilate(img_temp1, verticle_kernel, iterations=3)
    cv2.imwrite("./Temp/verticle_lines.jpg",verticle_lines_img)

    # Morphological operation to detect horizontal lines from an image
    img_temp2 = cv2.erode(img_bin, hori_kernel, iterations=3)
    horizontal_lines_img = cv2.dilate(img_temp2, hori_kernel, iterations=3)
    cv2.imwrite("./Temp/horizontal_lines.jpg",horizontal_lines_img)

    # Weighting parameters, this will decide the quantity of an image to be added to make a new image.
    alpha = 0.5
    beta = 1.0 - alpha
    # This function helps to add two image with specific weight parameter to get a third image as summation of two image.
    img_final_bin = cv2.addWeighted(verticle_lines_img, alpha, horizontal_lines_img, beta, 0.0)
    img_final_bin = cv2.erode(~img_final_bin, kernel, iterations=2)
    (thresh, img_final_bin) = cv2.threshold(img_final_bin, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # For Debugging
    # Enable this line to see verticle and horizontal lines in the image which is used to find boxes
    cv2.imwrite("./Temp/img_final_bin.jpg",img_final_bin)
    # Find contours for image, which will detect all the boxes
    contours, hierarchy = cv2.findContours(img_final_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # Sort all the contours by top to bottom.
    (contours, boundingBoxes) = sort_contours(contours, method="top-to-bottom")

    idx = 0
    for c in contours:
        # Returns the location and width,height for every contour
        x, y, w, h = cv2.boundingRect(c)

        # If the box height is greater then 20, widht is >80, then only save it as a box in "cropped/" folder.
        if (w > 80 and h > 20):
            idx += 1
            new_img = img[y:y+h, x:x+w]
            cv2.imwrite(cropped_dir_path+str(idx) + '.png', new_img)

    # For Debugging
    # Enable this line to see all contours.
    cv2.drawContours(img, contours, -1, (0, 0, 255), 3)
    cv2.imwrite("./Temp/img_contour.jpg", img)

def get_sum_students( group_id ) :
    request_url  = "https://localhost:5001/GroupApi?groupID="+str(group_id)
    request = requests.get( request_url, verify=False )
    if request.status_code == 200 :
        data = request.content 
        return data['sum']
    return -2

def get_student_name(row_cropped, width, counter) :
    student_name_cell = row_cropped[:, 0: (width // 10 ) ]
    cv2.imwrite("student_name"+ str(counter) +".png", student_name_cell) # enregistrer le cellule de nom
    img = cv2.imread("student_name"+ str(counter) +".png")
    custom_config = r'--oem 3 --psm 6'
    student_name = pytesseract.image_to_string(img, config=custom_config)
    return student_name

def black_or_white( cell ) :
    ret, cell_bin = cv2.threshold(cell,127,255,cv2.THRESH_BINARY) # tresh cell
    zeros = np.count_nonzero(cell_bin == 0)
    ones = np.count_nonzero(cell_bin == 255)
    return 1 if ones > zeros else 0 

def marked_hours( row_cropped, width, counter ):
    END_WIDTH = width // 20

    student_name = get_student_name( row_cropped, width, counter )
    start_width = 0
    end_width = width // 20
    table = []
    if student_name == None :
        student_name = ""
    table.append(student_name)
    for j in range( 20 ) : # 20 is number of cols in table
        counter = j+1
        if ( counter > 2  ) : # eviter les 5 premieres cellules du nom
            cell_cropped = row_cropped[:, start_width:end_width ]
            result = black_or_white( cell_cropped )
            table.append( result )
        start_width = end_width
        end_width += END_WIDTH
    return table

def box_cropping( box_url, sum_students ) :
    img = cv2.imread(box_url)  # Read the image
    height, width, _ = img.shape 
    END_HEIGHT = height // sum_students
    start_height = 0
    end_height = height // sum_students
    total = []


    for i in range ( sum_students ) : # le plus 1 est du header de la table
        counter = i+1
        if ( counter == 1 ) :
            start_height = end_height 
            end_height += END_HEIGHT
        else :
            row_cropped = img[start_height:end_height, :]
            hours = marked_hours( row_cropped, width, counter )
            total.append(hours)
            start_height = end_height 
            end_height += END_HEIGHT
    
    for i in range ( sum_student ) :
        counter = i+1
        if ( counter != 1 ) : os.remove("student_name"+i+".png")

    return total



if __name__ == '__main__':
    TestApp().run()