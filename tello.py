import socket
import threading
import cv2
import logging
import time



class Tello:

    #logger setup
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger('tello')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    #client port
    client_ip = ''
    client_port = 8889

    #video port
    video_ip = '0.0.0.0'
    video_port = 11111

    #state port
    state_port = 8890

    #time to wait before issuing new command
    wait_time = 0.5

    max_response_time = 7

    def __init__(self):

        tello_ip = '192.168.10.1'
        tello_port = 8889
        
        enable_exceptions = True
        retry_count = 3
        self.cap = None
        last_received_command = time.time()
        


        self.address = (tello_ip, tello_port)

        self.command_timeout = 0.3
        self.imperial = False
        self.response = None
        self.response_state = None  #to attain the response of the states
        self.stream_on = False
        self.enable_exceptions = enable_exceptions
        self.retry_count = retry_count


        #socket to communicate with Tello    
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # socket for sending commands
        self.socket_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # socket for receiving Tello state

        self.socket_client.bind(('', self.client_port))
        self.socket_state.bind(('', self.state_port))

        #create thread for receiving acknowledge/error from Tello
        thread1 = threading.Thread(target = self.receive_thread, args = ())
        thread1.daemon = True
        thread1.start()

        #create thread for receiving state from Tello
        thread2 = threading.Thread(target = self.get_state, args = ())
        thread2.daemon = True
        thread2.start()

    #Runs in background to get Tello state    
    def get_state(self):

        while True:
            try:
                self.response_state, _ = self.socket_state.recvfrom(128)
            except Exception as e:
                self.logger.error(e)
                break

   #Runs in background to get Tello responses 
    def receive_thread(self):

        while True:
            try:
                self.response, _ = self.socket_client.recvfrom(1024)
            except Exception as e:
                self.logger.error(e)
                break

    def video_address(self):

        return 'udp://@' + self.video_ip + ':' + str(self.video_port)  # + '?overrun_nonfatal=1&fifo_size=5000'


    #Get video capture from drone
    def video_capture(self):

        # if self.cap is None:
        #     self.cap = cv2.VideoCapture(self.get_udp_video_address())

        # if not self.cap.isOpened():
        #     self.cap.open(self.video_address())

        #while not self.stopped:
        self.frame = self.cap.read()
        return self.frame

    #Start video streaming        
    def video_capture_start(self):

        self.streamon()
        #threading.Thread(target=self.video_capture, args=()).start()
        self.cap = cv2.VideoCapture(self.video_address())
        self.cap.open(self.video_address())
        #self.stopped = False
        return self

    #Stop video streaming
    def video_capture_stop(self):

        self.streamoff()
        #self.stopped = True

    #Send command to Tello
    #param command: Command to send
    #return: Response from Tello (str)
    def send_command(self, command):

        time_diff = time.time() * 1000 - self.wait_time
        if time_diff < self.wait_time:
            time.sleep(time_diff)

        self.logger.info('Send command: ' + command)
        timestamp = int(time.time() * 1000)

        self.socket_client.sendto(command.encode('utf-8'), self.address)

        while self.response is None:
            if (time.time() * 1000) - timestamp > self.max_response_time * 1000:
                self.logger.warning('Timeout exceed on command ' + command)
                return False

        tello_response = self.response.decode('utf-8').rstrip("\r\n")

        self.logger.info('Response from Tello: ' + tello_response)

        self.response = None

        self.last_received_command = time.time() * 1000

        return tello_response

    #Send command to Tello
    #param command: Command to send
    #return: No Response from Tello
    def send_command_noreturn(self, command):

        self.logger.info('Send command (w/ no response): ' + command)
        self.socket_client.sendto(command.encode('utf-8'), self.address)

        '''
        Send control command to Tello
        If Ok response, return true
        If No/Error response, return false call command_error method
        
        command: entry SDK mode
        takeoff: Tello auto takeoff
        land: Tello auto land
        streamon: Set video stream on
        streamoff: Set video stream off
        emergency: Stop all motors immediately
        up x: Tello fly up with distance x cm. x: 20-500
        down x: Tello fly down with distance x cm. x: 20-500
        left x: Tello fly left with distance x cm. x: 20-500
        right x: Tello fly right with distance x cm. x: 20-500
        forward x: Tello fly forward with distance x cm. x: 20-500
        back x: Tello fly back with distance x cm. x: 20-500
        cw x: Tello rotate x degree clockwise x: 1-3600
        ccw x: Tello rotate x degree counter- clockwise. x: 1-3600
        speed x: set speed to x cm/s. x: 10-100

        '''
    def send_control_command(self, command):

        for i in range(0, self.retry_count):
            response = self.send_command(command)

            if response == 'OK' or response == 'ok':
                return True

        #return self.command_error(command, response, self.enable_exceptions)

    #Called if command is unsuccessful
    def command_error(command, response, enable_exceptions):
        
        message = 'Command ' + command + ' was unsuccessful. Response from Tello: ' + str(response)
        if enable_exceptions:
            raise Exception(message)
        else:
            self.logger.error(message)
            return False

    



##############################################################################################
                        ##### CONTROL COMMANDS FOR TELLO #####
##############################################################################################


    #methods return True or False if command was successful/unsuccessful
    def connect(self):

        result = self.send_control_command("command")

        return result

    def streamon(self):

        result = self.send_control_command("streamon")

        return result

    def streamoff(self):

        result = self.send_control_command("streamoff")

        return result 

    def takeoff(self):

        result = self.send_control_command("takeoff")

        return result 

    def land(self):

        result = self.send_control_command("land")

        return result 

    def emergency(self):

        result = self.send_control_command("emergency")

        return result 

    '''
        up x: Tello fly up with distance x cm.
        down x: Tello fly down with distance x cm.
        left x: Tello fly left with distance x cm.
        right x: Tello fly right with distance x cm.
        forward x: Tello fly forward with distance x cm.
        back x: Tello fly back with distance x cm.
        
        x: 20 - 500
    '''

    def move(self, direction, distance):

        if distance < 20:
            distance = 20

        elif distance > 500:
            distance = 500

        move_command = "%s %s" %(direction, distance)

        result = self.send_control_command(move_command)

        return result

    '''
        cw x: Tello rotate x degree clockwise.
        ccw x: Tello rotate x degree counter- clockwise.

        x: 1 - 3600
    
    '''
    def rotate(self, direction, angle):

        if angle < 1:
            angle = 1

        elif angle > 3600:
            angle = 3600

        rotate_command = "%s %s" %(direction, angle)

        result = self.send_control_command(rotate_command)

        return result

    '''
        speed x: set speed to x cm/s.

        x: 10-100 

    '''

    def set_speed(self, speed):

        if speed < 10:
            speed = 10

        elif speed > 100:
            speed = 100

        speed_command = "speed %s" %(speed)

        result = self.send_control_command(speed_command)

        return result


    def end(self):
      
        self.video_capture_stop()
        self.cap.release()

        
