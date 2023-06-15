import asyncio
from asyncio import StreamReader, StreamWriter
from datetime import datetime, timedelta
from threading import Timer

from consts import QUIT, NICKNAME, PRIVATE, DELAY, COMPLAIN, GREETING
from models import ClientModel
from logger import get_logger
from settings import Settings


logger = get_logger(__name__)
settings = Settings()


class Server:
    def __init__(
        self,
        ip: settings.IP,
        port: settings.PORT
    ):
        self._ip: str = ip
        self._port: int = port
        self._clients: dict[asyncio.Task, ClientModel] = {}
        logger.info('Сервер запустился на {}:{}.'.format(self.ip, self.port))

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def clients(self):
        return self._clients

    async def run(self):
        try:
            srv = await asyncio.start_server(self.get_client_data, self.ip, self.port)
            async with srv:
                await srv.serve_forever()
        except Exception as error:
            logger.error(error)
        except KeyboardInterrupt:
            logger.warning('Keyboard Interrupt Detected. Shutting down!')

    async def get_client_message(self, client_model: ClientModel):
        while True:
            msg = await client_model.get_message()
            if client_model.amount_of_messages == 0:
                client_model.first_message_date = datetime.now()
            if msg.startswith(QUIT):
                break
            elif msg.startswith('/'):
                self.handle_commands(client_model, msg)
            else:
                if self.check_ban_time(client_model):
                    self.send_broadcast_message('{}: {}'.format(client_model.nickname, msg).encode('utf8'))
                    client_model.amount_of_messages += 1
            logger.info('{}'.format(msg))
            await client_model.writer.drain()
        logger.info('Клиент отсоединился!')

    def get_client_data(self, reader: StreamReader, writer: StreamWriter):
        client_model = ClientModel(reader, writer)
        task = asyncio.Task(self.get_client_message(client_model))
        self.clients[task] = client_model
        writer.write(GREETING.encode())
        client_ip = writer.get_extra_info('peername')[0]
        client_port = writer.get_extra_info('peername')[1]

        logger.info('Новое соединение: {}:{}'.format(client_ip, client_port))
        task.add_done_callback(self.disconnect_client)

    @staticmethod
    def check_ban_time(client_model: ClientModel) -> bool:
        client_model.count_ban_time()
        client_model.count_time_to_ban_cancellation()
        if not client_model.amount_of_complaints < 3:
            client_model.send_message('Вы забанены!'.encode('utf8'))
        if not client_model.amount_of_messages <= 20:
            client_model.send_message('Вы достигли лимита по количеству сообщений - подождите 1 час.'.encode('utf8'))
        else:
            return True

    @staticmethod
    def parse_command(client_model: ClientModel, msg: str) -> str:
        msg = msg.split(' ')
        if len(msg) >= 2:
            return msg[1]
        else:
            logger.info('{} ввёл несуществующую команду.'.format(client_model.nickname))
            client_model.send_message('Несуществующая команда \n'.encode('utf8'))

    def send_message_at(self, client: ClientModel, message: str):
        now = datetime.now()
        through = self.parse_command(client, message)
        send_at = now + timedelta(minutes=int(through))
        delay = (send_at - now).total_seconds()
        msg = message.replace('/delay', '').replace('{}'.format(through), '{}: '.format(client.nickname)).encode()
        timer = Timer(delay, self.send_broadcast_message, args=(msg, ))
        timer.start()

    def complain_to_user(self, client_model: ClientModel, msg: str):
        complain_to = self.parse_command(client_model, msg)
        for target in self.clients.values():
            if target.nickname == complain_to:
                target.amount_of_messages += 1
                if target.amount_of_complaints == 3:
                    target.ban_date = datetime.now()

    def send_broadcast_message(self, msg: bytes, exclusion_list: list = []):
        logger.info(self.clients)
        for client in self.clients.values():
            if client not in exclusion_list:
                client.send_message(msg)

    def set_new_nickname(self, client_model: ClientModel, msg: str) -> None:
        new_nickname = self.parse_command(client_model, msg)
        if new_nickname is not None:
            client_model.nickname = new_nickname
            client_model.send_message('Nickname был изменён на {} \n'.format(client_model.nickname).encode('utf8'))
            return
        else:
            client_model.send_message('Введите команду /nickname <nickname>\n'.encode('utf8'))

    def send_private_message(self, client_model: ClientModel, msg):
        msg_for = self.parse_command(client_model, msg)
        if msg_for == client_model.nickname:
            client_model.send_message('Нельзя отправить сообщение самому себе!'.encode('utf8'))
        for target in self.clients.values():
            if msg_for == target.nickname:
                target.send_message((msg.replace('/private', 'Приватное сообщение от {}: '.format(
                    client_model.nickname)).replace('{}'.format(msg_for), '')).encode('utf8'))
            else:
                client_model.send_message('Пользователя с никнеймом {} не существует.'.format(msg_for).encode('utf8'))

    def disconnect_client(self, task: asyncio.Task):
        client = self.clients[task]
        self.send_broadcast_message('{} отсоединился!'.format(client.nickname).encode('utf8'), [client])
        del self.clients[task]
        client.send_message('/quit'.encode('utf8'))
        client.writer.close()

        logger.info('Соединение прервано.')

    def handle_commands(self, client_model: ClientModel, msg: str):
        msg = msg.replace('\n', '').replace('\r', '')

        match msg:
            case msg if msg.startswith(NICKNAME):
                self.set_new_nickname(client_model, msg)
            case msg if msg.startswith(COMPLAIN):
                self.complain_to_user(client_model, msg)
            case msg if msg.startswith(DELAY):
                self.send_message_at(client_model, msg)
            case msg if msg.startswith(PRIVATE):
                self.send_private_message(client_model, msg)
            case msg if msg.startswith(QUIT):
                self.disconnect_client(client_model, msg)
            case _:
                client_model.send_message('Такой команды не существует...\n'.encode('utf8'))


if __name__ == '__main__':
    server = Server(settings.IP, settings.PORT)
    asyncio.run(server.run())