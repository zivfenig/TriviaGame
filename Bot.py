import random
from client import *
import time
class BotClient(Client):

    def __init__(self):

        super().__init__()


    def get_username(self):
        """
        Get random username from player names
        :return: Bot name
        """
        name = 'Bot:' + random.choice(['Aviv_Cohavi', 'Moshe_Dayan', 'Rafael_Eitan', 'Yitzhak_Rabin', 'Yigal_Yadin', 'Yitzhak_Sadeh', 'David_Ben-Gurion',
                                       'Gadi_Eizenkot', 'Benny_Gantz', 'Dan_Halutz', 'Shaul_Mofaz', 'Gabi_Ashkenazi', 'Hertzi_Halevy'])
        self.color_print(f'Your name is: {name}', 'green')
        return name

    def get_user_input(self):
        """
        Get bot input
        :return: randmly selected input
        """
        time.sleep(random.randint(1, 3)) # sleep for random time between 1 and 3 seconds to simulate thinking
        return random.choice(['t', 'f'])

if __name__ == '__main__':
    try:
        bot_client = BotClient()
        bot_client.start()
    except KeyboardInterrupt:
        bot_client.color_print('Bot manually stopped', 'red')