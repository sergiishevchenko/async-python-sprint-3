import asyncio
from aioconsole import ainput
from asyncio import AbstractEventLoop, StreamReader, StreamWriter
from typing import Optional

from logger import get_logger

logger = get_logger(__name__)


class Client:
    def __init__(
        self,
        loop: AbstractEventLoop,
        ip: str = '127.0.0.1',
        port: int = 8000
    ):
        self._ip: str = ip
        self._port: int = port
        self._abstract_event_loop: AbstractEventLoop = loop
        self._stream_reader: StreamReader = None
        self._stream_writer: StreamWriter = None

    @property
    def server_ip(self):
        return self._ip

    @property
    def server_port(self):
        return self._port

    @property
    def loop(self):
        return self._abstract_event_loop

    @property
    def reader(self):
        return self._stream_reader

    @property
    def writer(self):
        return self._stream_writer

    async def connect_to_server(self):
        try:
            self._stream_reader, self._stream_writer = await asyncio.open_connection(self.server_ip, self.server_port)
            await asyncio.gather(self.get_messages_from_server(), self.start_chat())
            logger.info('Соединение установлено.')
        except Exception as ex:
            logger.error('Произошла ошибка: ', {ex})
        logger.info('Соединение с сервером прервано')

    async def get_message(self):
        return str((await self.reader.read(255)).decode('utf8'))

    async def get_messages_from_server(self):
        message: Optional[str] = None
        while message != 'quit':
            message_from_server = await self.get_message()
            await asyncio.sleep(0.1)
            print('{}'.format(message_from_server))

        if self.loop.is_running():
            self.loop.stop()
            logger.info('Цикл остановлен.')

    async def start_chat(self):
        message: str = None
        while message != '/quit':
            message = await ainput('')
            self.writer.write(message.encode('utf8'))
            await self.writer.drain()
            logger.info('Сообщение отправлено.')

        if self.loop.is_running():
            self.loop.stop()
            logger.info('Цикл остановлен.')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client = Client(loop)
    asyncio.run(client.connect_to_server())
