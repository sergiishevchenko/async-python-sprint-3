from asyncio import StreamReader, StreamWriter
from datetime import datetime


class ClientModel:
    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.stream_reader: StreamReader = reader
        self.stream_writer: StreamWriter = writer
        self.ip: str = writer.get_extra_info('peername')[0]
        self.port: int = writer.get_extra_info('peername')[1]
        self.nickname: str = str(writer.get_extra_info('peername'))
        self.ban_date: datetime = None
        self.first_message_date: datetime = None
        self.amount_of_complaints: int = 0
        self.amount_of_messages: int = 0

    def __str__(self):
        return '{} {}:{}'.format(self.nickname, self.ip, self.port)

    @property
    def reader(self):
        return self.stream_reader

    @property
    def writer(self):
        return self.stream_writer

    @property
    def server_ip(self):
        return self.ip

    @property
    def server_port(self):
        return self.port

    async def get_message(self) -> str:
        return str((await self.reader.read(255)).decode('utf8'))

    def send_message(self, msg: str) -> bytes:
        return self.writer.write(msg)

    def count_ban_time(self):
        if self.ban_date:
            time_delta = datetime.now() - self.ban_date
            if (time_delta.seconds/60) >= 240:
                self.amount_of_complaints = 0

    def count_time_to_ban_cancellation(self):
        if self.first_message_date:
            time_delta = datetime.now() - self.first_message_date
            if (time_delta.seconds/60) >= 60:
                self.amount_of_messages = 0
