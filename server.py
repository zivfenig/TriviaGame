# chtgpt link: https://chat.openai.com/share/a2b49ca9-cc93-4415-8216-873e54833c07
import os
import random
import socket
import sys
import threading
import time
from time import sleep





SERVER_NAME = 'IDF Trivia Server'
MAGIC_COOKIE = b'\xab\xcd\xdc\xba'
OFFER_MESSAGE_TYPE = b'\x02'
UDP_PORT = 13117


COLORS = {'reset':'\033[0m',
          'yellow':'\033[93m',
          'red':'\033[31m',
          'green':'\033[92m',
          'idf':'\033[32m',
          'purple':'\033[35m'
          }

PLAYER_COLORS = {'idf':'\033[32m', 'blue':'\033[94m', 'purple':'\033[35m', 'cyan':'\033[96m', 'pink':'\033[95m'}


server_online = threading.Event() # event to indicate that the server is online
game_started_event = threading.Event() # event to indicate that the game has started
everyone_answered_event = threading.Event() # event to indicate that all players have answered
round_started_event = threading.Event() # event to indicate that a new round has started

print_lock = threading.Lock() # lock for printing to the console
answers_lock = threading.Lock() # lock for accessing the answers dictionary
lock = threading.Lock() # current question lock
# variables to keep track of the fastest player and response time
fastest_player = ''
fastest_response_time = float('inf')

ACCEPT_TIMEOUT = 10
ANSWER_TIMEOUT = 10

WELCOME_MESSAGE = (f'Welcome to the {SERVER_NAME} where we are answering trivia questions about the Israeli Defence Forces')

questions = { "The Israel Defense Forces (IDF) was established in 1948.": "t",
    "IDF is one of the most technologically advanced militaries in the world.": "t",
    "All Israeli citizens, including women, are required to serve in the IDF.": "f",
    "IDF has mandatory military service for both men and women.": "t",
    "The IDF operates primarily in the Middle East region.": "t",
    "The Israeli Air Force is part of the IDF.": "t",
    "The Mossad is a branch of the IDF responsible for military intelligence.": "f",
    "The IDF primarily relies on conscripts and does not have a professional army.": "f",
    "IDF has been involved in several wars and conflicts since its establishment.": "t",
    "IDF operates land, air, and sea forces.": "t",
    "IDF has a strict policy of not allowing any foreign volunteers to serve.": "f",
    "Israel has compulsory military service for Arab citizens.": "f",
    "IDF is known for its extensive use of advanced military technology.": "t",
    "The Chief of the General Staff is the highest-ranking officer in the IDF.": "t",
    "IDF has a policy of 'purity of arms,' emphasizing moral conduct in combat.": "t",
    "IDF has never been involved in peacekeeping missions outside Israel.": "f",
    "The Golani Brigade is one of the infantry units in the IDF.": "t",
    "The IDF has never faced any significant challenges from neighboring countries.": "f",
    "The IDF has a strict policy of not allowing women to serve in combat roles.": "f",
    "IDF has faced criticism and allegations of human rights violations.": "t",
    "IDF has a dedicated unit for handling cyber warfare.": "t",
    "Israel spends a significant portion of its GDP on defense, primarily to fund the IDF.": "t",
    "The IDF has a reserve component that can be called up during times of need.": "t",
    "The IDF has never engaged in counter-terrorism operations.": "f",
    "IDF operates an Iron Dome system for missile defense.": "t",
    "The IDF has a policy of not allowing openly LGBTQ+ individuals to serve.": "f",
    "The IDF has historically relied on foreign military aid for its operations.": "t",
    "IDF has a strong emphasis on the principle of 'never leaving a soldier behind.'": "t",
    "The IDF has a separate branch dedicated to naval operations.": "t",
    "The IDF has never had any female generals.": "f"}

questions_hard_score = {} # dictionary to hold the score for each question e.g the number of mistakes each round
players_answered_events = {} # dictionary to hold events for each player, keys are sockets values are events
players_names = {} # dictionary to hold the names of the players keys are socekts and values are player's names
active_players_colors = {} # dictionary to hold the colors of the players keys are sockets values are colors    
disqualified_clients = [] # list to hold the clients that have been disqualified
playing_clients = [] # list to hold the clients that are still playing the game
current_question = ''
clients = [] # list to hold the clients that are connect to the server


def set_text_color(text, color):
    """
    Set text color
    :param text:
    :param color:
    :return: colored text
    """
    return COLORS[color] + text + COLORS['reset']

def server_print(text, color):
    """
    Print text in color
    :param text:
    :param color:
    :return: print color text only from a list of colors reserved for the server
    """
    print(COLORS[color] + text + COLORS['reset'])

def player_print(text, color):
    """
    Print text in color
    :param text:
    :param color:
    :return: print color text from a list of colors reserved for players
    """
    print(PLAYER_COLORS[color] + text + COLORS['reset'])


def set_current_question(value):
    """
    Set the current question
    :param value:

    """
    global current_question
    with lock: # lock the current question
        current_question = value


def get_current_question():
    """
    Get the current question
    :return:  the current question
    """

    global current_question
    with lock:
        return current_question

def translate_answer(answer):
    """
    Translate the answer to 't' or 'f'
    :param answer:
    :return: translated answer
    """
    if answer in ['y', 't', '1']:
        return 't'
    return 'f'


def update_fastest_player_statistics(player_name, response_time):
    """
    Update the fastest player statistics
    :param player_name:
    :param response_time:
    """
    global fastest_response_time
    global fastest_player
    if response_time < fastest_response_time:
        fastest_response_time = response_time
        fastest_player = player_name



def remove_client(client_socket):
    """
    Remove a client from the server
    :param client_socket:
    """
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close() # close the client socket


def remove_player(client_socket):
    """
    Remove a player from the game
    :param client_socket:
    """

    if client_socket in playing_clients:
        playing_clients.remove(client_socket) # remove the player from the playing clients list
    if client_socket in players_answered_events:
        players_answered_events[client_socket].set() # trigger the event to release the server from waiting for the player to answer

def add_to_disqualified(client):
    """
    Add a client to the disqualified list
    :param client:
    """
    disqualified_clients.append(client)


def assign_player_color(client_socket):
    """
    Assign a random color to a player
    :param client_socket:
    :return: the color assigned to the player
    """
    color = random.choice(list(PLAYER_COLORS.keys()))
    active_players_colors[client_socket] = color
    player_name = get_player_name(client_socket)

    if player_name.startswith('Bot:'): # if the player is a bot assign the color 'idf'
        color = 'idf'
    return color


def get_player_name(client_socket):
    """
    Get the name of a player by the client socket
    :param client_socket:
    :return: the name of the player
    """
    return players_names[client_socket]


def receive_player_name(client_socket):
    """
    Receive the name of a player initally when the game starts
    :param client_socket:
    :return: player name
    """
    player_name = ''
    try:
        player_name = client_socket.recv(1024).decode() # receive the name from the client
        players_names[client_socket] = player_name # add the player name to the dictionary
    except (ConnectionAbortedError, socket.timeout):
        if client_socket in players_answered_events:
            players_answered_events[client_socket].set() # trigger the event to release the server from waiting for the client to answer
        remove_client(client_socket) # remove the client from the server
        return 'failed'

    return player_name


def client_thread(client_socket):
    """
    The client thread that handles the client connection and recieves players answers
    :param client_socket:
     """
    client_socket.settimeout(ANSWER_TIMEOUT) # set client response timeout
    player_name = receive_player_name(client_socket)
    if player_name == 'failed': # if the player name is failed means the client did not send the name
        return

    player_color = assign_player_color(client_socket)
    with print_lock: # To avoid multiple threads printing at the same time
        player_print(f'Player {player_name}, joined the game.', f'{player_color}')
    game_started_event.wait() # blocking all the threads until the game starts i.e the event is set (become true)
    while client_socket in clients and client_socket in playing_clients: # while the client is connected and playing
        round_started_event.wait() # blocking all the threads until the round starts i.e the event is set (become true)
        question = get_current_question()
        if question == 'game over' or client_socket not in playing_clients: # if the player lost or the game is over (no more questions)
            remove_player(client_socket) # remove the player from playing clients list
            return
        correct_answer = questions[question]
        answer = 'FAILED'
        start_time = time.time() # start the timer to calculate the response time
        try:
            answer = client_socket.recv(1024).decode() # receive the answer from the client
        except socket.timeout: # if the client did not answer in the time limit (10 seconds)
            if client_socket in disqualified_clients: # if the client is already disqualified remove him to avoid loop of not answering
                remove_player(client_socket)
                with print_lock:
                    server_print(f'{player_name} disconnected', 'red')
                return # the player is stop playing
            else:
                add_to_disqualified(client_socket) # add the client to the disqualified list

                with print_lock:
                    server_print(f'{player_name} timeout', 'red')
                continue # continue to the next round

        except OSError: # if the client disconnected (all the possible connection exception)
            remove_player(client_socket)
            with print_lock:
                server_print(f'{player_name} disconnected', 'red')
            return
        end_time = time.time() # end the timer to calculate the response time
        if answer == 'FAILED' or answer == '': # if the client disconnected or timeout
            remove_player(client_socket)
            with print_lock:
                server_print(f'{player_name} disconnected', 'red')
            return

        response_time = end_time - start_time # calculate the response time
        update_fastest_player_statistics(player_name, response_time)

        answer = translate_answer(answer) # translate the answer to the correct format
        if answer == correct_answer:
            colored_text = f'{player_name}' + set_text_color(' is correct', 'green')
            with print_lock:
                player_print(colored_text, f'{player_color}')
        else:
            colored_text = f'{player_name}' + set_text_color(' is incorrect', 'red')
            with print_lock:
                player_print(colored_text, f'{player_color}')
            add_to_disqualified(client_socket) # add the client to the disqualified list if the answer is incorrect
            with lock:
                 questions_hard_score[question] += 1 # increase the question hard score
        if client_socket in players_answered_events: # if the client finished answering the question
            players_answered_events[client_socket].set() # trigger the event to release the server from waiting for the client to answer
        everyone_answered_event.wait() # blocking all the threads until all the clients answer the question i.e the event is set (become true)


def broadcast_udp(udp_socket, message, server_ip, server_port):
    """
    Broadcast a offer announcement to all the clients in the same network
    :param udp_socket:
    :param message:
    """
    while True:
        udp_socket.sendto(message, ('255.255.255.255', UDP_PORT)) # send the offer to all the clients in the network
        sleep(1) #Broadcast every 1 second

def broadcast_tcp(message):
    """
    Broadcast a message to all the clients
    :param message:

    """
    for client in clients:
        try:
            client.sendall(message.encode())
        except OSError: # if the client disconnected (all the possible connection exception)
            clients.remove(client)
            if client in playing_clients:
                playing_clients.remove(client) # remove the client from the playing clients list
            if client in players_answered_events:
                players_answered_events[client].set() # trigger the event to release the server from waiting for the client to answer


def shuffle_questions(questions):
    """
    Shuffle the questions to be random
    :param questions:
    :return: shuffled questions
    """
    keys = list(questions.keys())
    random.shuffle(keys)
    return {key: questions[key] for key in keys}

def generate_active_players_names_list(message):
    """
    Generate the active players names list in each round
    :param message:
    :return: active players message
    """
    for i, client_socket in enumerate(playing_clients):
        if i == len(playing_clients) - 1:
            message += players_names[client_socket]
        else:
            message += players_names[client_socket] + ' and '
    message += ':'
    return message



def active_players_names_list():
    """
    Generate the active players names list in each round with thier number e.g Player 1: Yossi, Player 2: Gal, ...
    :return: active players message
    """
    message = '\n'
    for i, client_socket in enumerate(players_names):
        message += f'Player {i+1}: {players_names[client_socket]} \n'
    message += '=='
    return message

def find_available_port():
    """
    Find an available port to bind the socket
    :return: available port
    """
    test = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test.bind(('', 0)) # bind the socket to any available port
    return test.getsockname()[1] # get the port number


def remove_all_disqualified_players():
    """
    Remove all the disqualified players from the playing clients list and
    set the event to release the server from waiting for the client to answer

    """
    for client in disqualified_clients:
        if client in playing_clients:
            playing_clients.remove(client)
        if client in players_answered_events:
            players_answered_events[client].set() # trigger the event to release the server from waiting for the client to answer

def game_state(first_round_done):
    """
    Check the game state to decide if the game should continue or end
    :param first_round_done:
    :return: game state
    """
    connected_players_count = len(clients)
    playing_players_count = len(playing_clients)

    if playing_players_count == 0: # if there are no playing players
        return 'END_GAME'
    if playing_players_count == 1 and first_round_done: # if there is a winner and the first round is done
        return 'WINNER'
    return 'CONTINUE_GAME'

def generate_statistics_message():
    """
    Generate the statistics message to be sent to all the clients
    :return:
    """
    statistics_message = 'Statistics:\n'
    hardest_question = max(questions_hard_score, key=lambda k: questions_hard_score[k]) # get the hardest question i.e the question that the players got wrong the most
    hardest_question_score = questions_hard_score[hardest_question]
    if hardest_question_score > 0:
        statistics_message += f'\U0001F92F The hardest question: {hardest_question} {hardest_question_score} players got wrong \n'
    if fastest_response_time != float('inf'):
        statistics_message += f'\U0001F525 Fastest player: {fastest_player} at {round(fastest_response_time, 2)} sec \n'
    return statistics_message


def announce_winner(client_socket):
    """
    Announce the winner to all the clients
    :param client_socket:
    :return: the winner announcement message
    """
    player_name = get_player_name(client_socket)
    winner_announcement = f'Congratulations the winner: {player_name}'
    broadcast_tcp(winner_announcement) # broadcast the winner announcement to all the clients
    remove_client(client_socket) # remove the winner from the clients list
    return winner_announcement


def start_udp_server(udp_server_socket, ip_address, tcp_port):
    """
    Start the UDP server and build the offer announcement message
    :param udp_server_socket:
    :param ip_address:
    :param tcp_port:
    """

    offer_announcement = MAGIC_COOKIE + OFFER_MESSAGE_TYPE + SERVER_NAME.encode().ljust(32) + tcp_port.to_bytes(2, 'big') # build the offer announcement message
    udp_thread = threading.Thread(target=broadcast_udp, args=(udp_server_socket, offer_announcement, ip_address, UDP_PORT)) # start an independent thread to broadcast the offer announcement
    udp_thread.start()


def start_tcp_server(ip_address, tcp_port):
    """
    Start the TCP server and accept the clients connections opening a new thread for each client
    :param ip_address:
    :param tcp_port:
    :return: tcp server socket
    """
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create a TCP socket
    tcp_server_socket.bind((ip_address, tcp_port)) # bind the socket to the IP address and port
    tcp_server_socket.listen(socket.SOMAXCONN) # listen for incoming connections with a maximum possible number of connections
    players_names.clear()
    clients.clear()
    playing_clients.clear()
    try:
        while True:
            connection, address = tcp_server_socket.accept() # accept the client connection and get the client socket and address
            tcp_server_socket.settimeout(ACCEPT_TIMEOUT) # set a timeout for the accept method to avoid blocking
            clients.append(connection) # add the client socket to the clients list
            playing_clients.append(connection) # add the client socket to the playing clients list
            thread_client = threading.Thread(target=client_thread, args=(connection,)) # start a new thread for the client
            thread_client.start()
    except socket.timeout: # if the accept method times out the game starts with the connected clients
        pass

    tcp_server_socket.settimeout(None) # remove the timeout from the socket
    return tcp_server_socket


def start_server():
    """
    Start tcp and udp servers and handle the game logic
    """
    global questions
    ip_address = socket.gethostbyname(socket.gethostname()) # get the IP address of the server
    tcp_port = find_available_port() # find an available port to bind the TCP socket
    udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # create a UDP socket
    udp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # set the socket to broadcast mode
    start_udp_server(udp_server_socket, ip_address, tcp_port) # start the UDP server

    while True:
        playing_clients.clear()
        players_names.clear()
        game_started_event.clear()
        questions = shuffle_questions(questions) # shuffle the questions list
        for question in questions:
            questions_hard_score[question] = 0  # initialize the questions hard score dictionary to 0 for each question
        with print_lock:
            server_print(f'Server started, listening on IP address {ip_address}', 'green')
        tcp_server_socket = start_tcp_server(ip_address, tcp_port) # accept the clients connections and start the TCP server
        game_started_event.set() # set the game started event to notify the threads that the game has started
        welcome_with_players_list = WELCOME_MESSAGE + active_players_names_list()
        broadcast_tcp(welcome_with_players_list) # broadcast the welcome message with the active players list to all the clients

        first_round_done = False # initialize the first round done flag to False
        for i, question in enumerate(questions):
            global round_started_event
            global everyone_answered_event
            global players_answered_events
            everyone_answered_event = threading.Event()
            with answers_lock:
                players_answered_events.clear() # clear the players answered events dictionary
                for client_socket in playing_clients:
                    players_answered_events[client_socket] = threading.Event() #initialize each player answered event to False

            round_started_event.clear() # initialize the round started event to False

            players_count = len(playing_clients)
            if game_state(first_round_done) == 'END_GAME' or game_state(first_round_done) == 'WINNER': # check if the game has ended or there is a winner
                break
            the_question = question
            set_current_question(the_question)

            with print_lock:
                if first_round_done:
                    print(generate_active_players_names_list(f'Round {i+1}, played by '))
                server_print(f'\U0001F914 True or False: {the_question}', 'yellow')

            round_started_event.set() # set the round started event to notify the threads that the round has started
            broadcast_tcp(f'True or False: {the_question}') # broadcast the question to all the clients
            for client_socket in players_answered_events:
                players_answered_events[client_socket].wait() # wait for the threads to answer the question
            everyone_answered_event.set() # set the everyone answered event to notify the threads that everyone has answered the question
            round_started_event = threading.Event() # initialize the round started event to False
            if len(playing_clients) == len(disqualified_clients) and players_count > 1: # check if all the players are disqualified and there are more than one player
                with print_lock:
                    server_print('Everyone is wrong, moving on...', 'red')
            else:
                remove_all_disqualified_players() # remove all the disqualified players from the playing clients list
            disqualified_clients.clear() # clear the disqualified clients list
            first_round_done = True

        set_current_question('game over') # no more questions, set the current question to game over

        if game_state(first_round_done) == 'WINNER': # check if there is a winner
            winner_socket = playing_clients[0] # get the winner socket he is the only one left in the playing clients list
            with print_lock:
                server_print(f'Congratulations the winner: {players_names[winner_socket]}', 'purple')
            announce_winner(winner_socket) # use announce winner function to send the winner message to all clients
        tcp_server_socket.close() # close the TCP server socket
        with print_lock:
            server_print(f'{generate_statistics_message()}', 'red') # print the statistics message
            server_print('game over, sending out offer requests...', 'green')


if __name__ == '__main__':
    try:
        start_server()
    except KeyboardInterrupt:
        with print_lock:
            server_print('Server shutting down...', 'red')
       # shutdown_server()

