import random
import socket


UDP_PORT = 13117
MAGIC_COOKIE = b'\xab\xcd\xdc\xba'
OFFER_MESSAGE_TYPE = b'\x02'

CONNECT_TIMEOUT = 10 # connection timeout in seconds

PLAYER_NAMES = ['Golani-12', 'Golani-13', 'Golani-51',
                'Givati-Tzabar', 'Givati-Rotem', 'Givati-Shaked',
                'Kfir-Lavi',
                'Sherion-71', 'Sherion-77',
                'Tzanhanim-101', 'Tzanhanim-890', 'Tzanhanim-202',
                'Handasa-601', 'Handasa-603', 'Handasa-605',
                'Nahal-932', 'Nahal-931', 'Nahal-50', 'Magal',
                'Duvdevan', 'Egoz', 'Yahalom', 'Shaldag', 'Haruv', 'Oketz', 'Shayetet-13', 'Matkal', 'Magalan', '669']







COLORS = {'yellow':'\033[93m', 'green':'\033[92m', 'red':'\033[31m', 'blue':'\033[94m', 'purple':'\033[95m', 'reset':'\033[0m'}



class Client:

    def __init__(self):
        pass

    def color_print(self, text, color):
        """
        Print text in color
        :param text:
        :param color:
        :return:
        """
        print(COLORS[color] + text + COLORS['reset'])


    def is_invalid_answer(self, answer):
        """
        Check if the answer is invalid before sending it to the server
        :param answer:
        :return: True if the answer is invalid, False otherwise
        """
        return not (answer.lower() in ['y', 't', '1', 'n', 'f', '0'])

    def get_username(self):
        """
        Get random username from player names
        :return: user name
        """
        name = random.choice(PLAYER_NAMES)
        self.color_print (f'Your name is: {name}', 'green')
        return name


    def get_user_input(self):
        """
        Get user input
        :return: user input
        """
        user_input = input('your answer: ').strip()
        while self.is_invalid_answer(user_input): # check if the answer is invalid
            user_input = input('you answer: ').strip()
        return user_input

    def start_udp_client(self):
        """
        Start UDP client and listen for offer message
        :return: server address, server port, server name
        """
        udp_connected = False # flag to indicate if the client is connected to the server

        udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # create UDP socket
        udp_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # set socket option to reuse address and port number
        udp_client_socket.bind(('', UDP_PORT)) # bind the socket to the port

        server_name = ''
        server_address = ''
        server_tcp_port = 0

        while not udp_connected: # loop until the client is connected to the server
            data, address = udp_client_socket.recvfrom(1024) # receive data from the server
            server_address = address[0] # get the server address from the address tuple
            if data.startswith(MAGIC_COOKIE + OFFER_MESSAGE_TYPE): # check if the message is a valid offer message
                udp_connected = True # set the flag to True to exit the loop
                server_name = data[5:37].strip().decode() # get the server name from the message
                server_tcp_port = int.from_bytes(data[37:39], 'big') # get the server TCP port from the message
            else:
                self.color_print('Invalid cookie or message type', 'red')

        udp_client_socket.close() # close the UDP socket after the client is connected to the server
        return server_address, server_tcp_port, server_name

    def start_tcp_client(self, server_address, server_port):
        """
        Start TCP client and connect to the server
        :param server_address:
        :param server_port:
        :return: tcp client socket
        """
        tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket
        try:
            tcp_client_socket.connect((server_address, server_port)) # connect to the server
            user_name = self.get_username() # get random user name
            tcp_client_socket.sendall(user_name.encode()) # send the user name to the server
            welcome_message = tcp_client_socket.recv(1024).decode() # receive welcome message from the server
            self.color_print(welcome_message, 'blue')
        except OSError: # handle connection error (all possible connection errors)
            self.color_print("Server disconnected",'red')
            return "BAD"
        except KeyboardInterrupt:
            self.color_print('Client shut down manually', 'red')
        return tcp_client_socket


    def start(self):
        """
        Start the client and connect to the server
        :return:
        """
        while True: #Game loop
            self.color_print(f'Client started, listening for offer requests...', 'green')
            server_address, server_tcp_port, server_name = self.start_udp_client() # start UDP client and listen for offer message
            self.color_print(f'Received offer from server "{server_name}" at address {server_address}, port {server_tcp_port}, attempting to connect...', 'green')


            client_socket = self.start_tcp_client(server_address, server_tcp_port) # start TCP client and connect to the server
            if client_socket == 'BAD': # check if the client fail to connect to the server
                continue #Try again to connect to the server
            try:
                while True: #Round loop
                    client_socket.settimeout(10) # set timeout for the client socket
                    message = client_socket.recv(1024).decode()
                    if message == '' or message == 'game over': # check if queestions finished or the server disconnected
                        self.color_print('Game over!', 'red')
                        break
                    if message.startswith('Congratulations'): # check if the message is a congratulations message
                        self.color_print('Game over!\n' + message, 'blue')
                        client_socket.close()
                        break
                    self.color_print(f'{message}', 'yellow')
                    user_answer = self.get_user_input() # get user input
                    client_socket.sendall(user_answer.encode()) # send the user input to the server
            except socket.timeout: # handle timeout error i,e the client didn't answer the server in 10 seconds
                self.color_print('connection timeout', 'red')
            except (ConnectionResetError, ConnectionAbortedError, OSError): # handle connection error (all possible connection errors)
                self.color_print(f'server disconnected, game over', 'red')
            finally:
                client_socket.close() # close the client socket anyway
            self.color_print('Server disconnected listening for offer request...', 'green')

if __name__ == '__main__':
    try:
        client = Client()
        client.start()
    except KeyboardInterrupt:
        client.color_print('Client shut down manually', 'red')


